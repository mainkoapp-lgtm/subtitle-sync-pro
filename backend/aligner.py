# [COMPLETED: 2026-04-11] 진행률 업데이트 세분화 및 취소 콜백(Cancellation) 로직 연동 완료 (임의 수정 금지)
import re
from typing import List, Dict, Optional
from google import genai
from google.genai import types 
import json
import time
from logger_config import logger

class SubtitleBlock:
    def __init__(self, index: int, start: str, end: str, text: str):
        self.index = index
        self.start = start
        self.end = end
        self.text = text

    def to_dict(self):
        return {
            "index": self.index,
            "start": self.start,
            "end": self.end,
            "text": self.text
        }

def ms_to_srt_time(ms: int) -> str:
    """밀리초를 SRT 시간 형식(HH:MM:SS,mmm)으로 변환"""
    s, ms = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def parse_srt(content: str) -> List[SubtitleBlock]:
    blocks = []
    # 1. 다양한 줄바꿈 통합 (\r\n -> \n)
    content = content.replace('\r\n', '\n').strip()
    
    # 2. 보편적인 SRT 블록 분할 (숫자 인덱스 앞의 빈 줄 기준)
    # \n\n 혹은 \n\d+\n으로 분할 시도
    raw_blocks = re.split(r'\n\s*\n', content)
    
    # 만약 블록 분할이 안 되었다면 (줄바꿈이 하나인 경우)
    if len(raw_blocks) < 2:
        # 인덱스 번호를 기준으로 강제 분할 시도
        raw_blocks = re.split(r'\n(?=\d+\n\d{2}:\d{2}:\d{2})', "\n" + content)
    
    for raw in raw_blocks:
        lines = [l.strip() for l in raw.split('\n') if l.strip()]
        if len(lines) >= 3:
            try:
                # 인덱스 추출 (숫자만 포함된 줄 혹은 첫 줄의 숫자)
                idx_match = re.search(r'\d+', lines[0])
                if not idx_match: continue
                idx = int(idx_match.group())
                
                # 시간 정보 (항상 '-->' 포함)
                time_line = ""
                text_start_idx = 2
                for i, line in enumerate(lines):
                    if '-->' in line:
                        time_line = line
                        text_start_idx = i + 1
                        break
                
                if not time_line: continue
                
                times = time_line.split(' --> ')
                start = times[0].strip()
                end = times[1].strip()
                text = " ".join(lines[text_start_idx:]).strip()
                
                # HTML 태그 제거 (공백으로 치환하여 단어 붙음 방지)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    blocks.append(SubtitleBlock(idx, start, end, text))
            except (ValueError, IndexError):
                continue
    return blocks

def parse_smi(content: str) -> List[SubtitleBlock]:
    """SMI (SAMI) 자막 파싱"""
    blocks = []
    # 1. SYNC 태그를 기준으로 분할
    sync_points = re.findall(r'<SYNC Start=(\d+)>', content, re.IGNORECASE)
    # 2. 각 SYNC 사이의 텍스트 추출
    # re.DOTALL을 사용하여 줄바꿈 포함 매칭
    contents = re.split(r'<SYNC Start=\d+>', content, flags=re.IGNORECASE)[1:]
    
    temp_blocks = []
    for i in range(len(sync_points)):
        start_ms = int(sync_points[i])
        text_raw = contents[i].strip()
        
        # HTML 태그 및 &nbsp; 제거 (공백으로 치환하여 단어 붙음 방지)
        text = re.sub(r'<[^>]+>', ' ', text_raw, flags=re.IGNORECASE)
        text = re.sub(r'&nbsp;', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if text:  # 텍스트가 있는 경우만 유효 블록으로 간주
            temp_blocks.append({
                "start_ms": start_ms,
                "text": text
            })
            
    # 3. 종료 시간 결정 (다음 SYNC의 시작 시간 혹은 +3초)
    for i in range(len(temp_blocks)):
        curr = temp_blocks[i]
        start_time = ms_to_srt_time(curr["start_ms"])
        
        if i < len(temp_blocks) - 1:
            end_time = ms_to_srt_time(temp_blocks[i+1]["start_ms"])
        else:
            end_time = ms_to_srt_time(curr["start_ms"] + 3000)
            
        blocks.append(SubtitleBlock(i + 1, start_time, end_time, curr["text"]))
        
    return blocks

def parse_subtitles(content: str, filename: str = "") -> List[SubtitleBlock]:
    """확장자 및 내용에 따라 적절한 파서 호출"""
    ext = filename.split('.')[-1].lower() if filename else ""
    
    if ext == 'smi' or '<SAMI>' in content.upper():
        logger.info(f"SMI 자막 감지됨: {filename}")
        return parse_smi(content)
    else:
        logger.info(f"SRT 자막 감지됨: {filename}")
        return parse_srt(content)

def calculate_similarity(text1: str, text2: str) -> float:
    # 1. 기본 텍스트 정규화
    t1 = re.sub(r'[^\w\s]', '', text1.lower())
    t2 = re.sub(r'[^\w\s]', '', text2.lower())
    
    words1 = set(t1.split())
    words2 = set(t2.split())
    
    # 2. 단어 겹침 (동일 언어 혹은 외래어 포함 시)
    text_score = 0.0
    if words1 and words2:
        intersection = words1.intersection(words2)
        text_score = len(intersection) / max(len(words1), len(words2))
    
    # 3. 숫자 매칭 (매우 강력한 다국어 힌트)
    nums1 = set(re.findall(r'\d+', text1))
    nums2 = set(re.findall(r'\d+', text2))
    num_score = 0.0
    if nums1 and nums2:
        num_intersection = nums1.intersection(nums2)
        num_score = len(num_intersection) / max(len(nums1), len(nums2))
    
    # 4. 문장 부호 패턴 (..., !!!, ??? 등)
    punc1 = "".join(re.findall(r'[!?\.]{2,}', text1))
    punc2 = "".join(re.findall(r'[!?\.]{2,}', text2))
    punc_score = 0.0
    if punc1 and punc1 == punc2:
        punc_score = 0.5
    
    # 5. 길이 유사성 (단어 수 비율)
    len1 = len(text1.split())
    len2 = len(text2.split())
    len_ratio = min(len1, len2) / max(len1, len2) if max(len1, len2) > 0 else 0
    
    # 최종 점수 조합 (가중치 적용)
    # 텍스트 겹침이 있으면 우선순위, 없으면 숫자와 구조 점수 활용
    final_score = text_score * 1.0 + num_score * 0.8 + punc_score * 0.2
    
    # 만약 모든 점수가 0이라면 최소한의 길이 유사도라도 반영 (오차범위 내)
    if final_score == 0:
        final_score = len_ratio * 0.01 
        
    return final_score

def gemini_batch_match(ref_window: List[SubtitleBlock], target_window: List[SubtitleBlock], api_key: str, model_name: str = "gemini-3.1-flash-lite-preview") -> Dict[int, int]:
    try:
        # 최신 SDK 2026 규격: genai.Client 사용
        client = genai.Client(api_key=api_key)
        
        ref_data = [{"idx": b.index, "text": b.text} for b in ref_window]
        target_data = [{"idx": b.index, "text": b.text} for b in target_window]
        
        prompt = f"""
        Analyze the following subtitles from the same video. 
        Match each Reference subtitle to the most semantically equivalent Target subtitle.
        
        Reference: {json.dumps(ref_data, ensure_ascii=False)}
        Target: {json.dumps(target_data, ensure_ascii=False)}
        
        Return a JSON object mapping Reference index to Target index.
        Example format: {{"1": 10, "2": 11}}
        If a match is extremely uncertain, use null.
        """
        
        # 신규 호출 방식: response_mime_type="application/json" 활용
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        # API 소량 로깅 추가
        if response.usage_metadata:
            logger.info(f"AI 매칭 API 사용량: {response.usage_metadata}")
            
        mapping = response.parsed
        if not mapping:
            # 보조 파싱 (문자열인 경우)
            mapping = json.loads(response.text)
            
        # 문자열 키를 정수로 변환
        return {int(k): v for k, v in mapping.items() if v is not None}
    except Exception as e:
        logger.error(f"Gemini API 호출 실패: {str(e)}")
        return {}

def fill_missing_subtitles(results: List[Dict], api_key: str, model_name: str, progress_callback=None, check_cancel=None, target_lang: str="ko") -> List[Dict]:
    lang_map = {"ko": "Korean", "en": "English", "ja": "Japanese", "zh": "Chinese", "hi": "Hindi", "es": "Spanish", "fr": "French", "de": "German"}
    target_lang_name = lang_map.get(target_lang, "Korean")
    try:
        client = genai.Client(api_key=api_key)
        
        missing_indices = [i for i, r in enumerate(results) if not r.get("matched", False)]
        if not missing_indices:
            return results
            
        logger.info(f"누락된 자막 번역 보완 시작 (총 {len(missing_indices)}개 발견)")
        
        # 1. 스타일 샘플 추출
        matched_results = [r for r in results if r.get("matched", False) and not r.get("translated", False)]
        sample_size = min(20, len(matched_results))
        samples = []
        if sample_size > 0:
            step = max(1, len(matched_results) // sample_size)
            for i in range(0, len(matched_results), step):
                if len(samples) >= sample_size:
                    break
                r = matched_results[i]
                samples.append({"original": r["ref"]["text"], "translated": r["target"]["text"]})
                
        # 2. 배치 번역 진행
        batch_size = 30
        for i in range(0, len(missing_indices), batch_size):
            if check_cancel and check_cancel():
                raise Exception("Cancelled")
            
            try:
                if progress_callback:
                    progress_callback(80 + int((i / len(missing_indices)) * 20))
                    
                batch_idxs = missing_indices[i:i + batch_size]
                batch_data = [{"id": idx, "text": results[idx]["ref"]["text"]} for idx in batch_idxs]
                
                prompt = f"""
                You are an expert subtitle translator.
                Translate the following missing subtitles into {target_lang_name}.
                Maintain the tone, style, and character voice matching the provided samples.

                [IMPORTANT] Strictly follow standard grammar and spacing rules of {target_lang_name}.
                Ensure that there are no missing or redundant spaces between words according to its native linguistic rules.
    
                [Style Samples (Original -> {target_lang_name})]
                {json.dumps(samples, ensure_ascii=False)}
    
                [Missing Subtitles to Translate]
                {json.dumps(batch_data, ensure_ascii=False)}
    
                Return a JSON object mapping the 'id' to its translated 'text'.
                Example format: {{"0": "번역된 문장 1", "5": "번역된 문장 2"}}
                """
                
                logger.info(f"AI 번역 보완 중... ({min(i + batch_size, len(missing_indices))}/{len(missing_indices)})")
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                
                # API 사용량 로깅 추가
                if response.usage_metadata:
                    logger.info(f"AI 번역 보완 API 사용량: {response.usage_metadata}")
                
                mapping = response.parsed
                if not mapping:
                    raw_text = response.text.strip()
                    # 마크다운 태그가 포함되어 있다면 제거
                    if raw_text.startswith("```json"):
                        raw_text = raw_text[7:]
                    elif raw_text.startswith("```"):
                        raw_text = raw_text[3:]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[:-3]
                    mapping = json.loads(raw_text.strip())
                    
                for idx_str, translated_text in mapping.items():
                    idx_int = int(idx_str)
                    ref_info = results[idx_int]["ref"]
                    results[idx_int]["target"] = {
                        "index": ref_info["index"],
                        "start": ref_info["start"],
                        "end": ref_info["end"],
                        "text": translated_text
                    }
                    results[idx_int]["target_index"] = ref_info["index"]
                    results[idx_int]["matched"] = True
                    results[idx_int]["translated"] = True
                    results[idx_int]["score"] = 1.0
                    
                time.sleep(0.5)
            except Exception as batch_e:
                logger.error(f"Gemini 번역 보완 배치 처리 실패 (부분 스킵): {str(batch_e)}")
                continue
            
    except Exception as e:
        logger.error(f"Gemini 번역 보완 초기 설정 실패: {str(e)}")
        
    if progress_callback:
        progress_callback(100)
        
    return results

def align_subtitles(ref_subs: List[SubtitleBlock], target_subs: List[SubtitleBlock], api_key: Optional[str] = None, ai_model: str = "gemini-3.1-flash-lite-preview", progress_callback=None, check_cancel=None, target_lang: str = "ko") -> List[Dict]:
    results = []
    total_ref = len(ref_subs)
    total_target = len(target_subs)
    target_map = {s.index: s for s in target_subs}
    used_targets = set()  # 중복 매칭 방지 플래그
    
    logger.info(f"자막 동기화 프로세스 시작 (AI 모델: {ai_model if api_key else 'None'})")
    
    # 1. AI 사전 매칭 (선택 사항)
    ai_mapping: Dict[int, int] = {}
    if api_key:
        batch_size = 30
        for i in range(0, total_ref, batch_size):
            if check_cancel and check_cancel():
                raise Exception("Cancelled")
            
            if progress_callback:
                progress_callback(max(5, int((i / max(total_ref, 1)) * 60)))
            ref_batch = ref_subs[i:i + batch_size]
            progress = i / total_ref
            approx_target_idx = int(progress * total_target)
            search_start = max(0, approx_target_idx - 50)
            search_end = min(total_target, approx_target_idx + 100)
            target_range = target_subs[search_start:search_end]
            
            logger.info(f"AI 분석 중... ({min(i + batch_size, total_ref)}/{total_ref})")
            batch_map = gemini_batch_match(ref_batch, target_range, api_key, ai_model)
            ai_mapping.update(batch_map)
            time.sleep(0.5) 
            
    # 2. 하이브리드 매칭 (AI 결과 우선 + 알고리즘 보완)
    target_idx = 0
    for idx, ref in enumerate(ref_subs):
        if check_cancel and idx % 20 == 0 and check_cancel():
            raise Exception("Cancelled")
            
        if progress_callback and idx % 20 == 0:
            base_p = 60 if api_key else 0
            remaining_p = 20 if api_key else 80
            progress_callback(base_p + int((idx / max(total_ref, 1)) * remaining_p))
            
        current_best_match = None
        max_score = 0.0
        
        # AI 결과가 있는 경우 우선 적용
        if ref.index in ai_mapping:
            matched_idx = ai_mapping[ref.index]
            if matched_idx in target_map and matched_idx not in used_targets:
                current_best_match = target_map[matched_idx]
                max_score = 1.0 # AI가 보증한 매칭
                
        # AI 결과가 없거나 실패한 경우 알고리즘으로 찾기
        if current_best_match is None:
            ref_progress = idx / total_ref if total_ref > 0 else 0
            # 윈도우 탐색
            search_start = max(0, target_idx - 20)
            search_end = min(total_target, target_idx + 40)
            
            for i in range(search_start, search_end):
                target = target_subs[i]
                if target.index in used_targets:
                    continue
                
                target_progress = i / total_target if total_target > 0 else 0
                pos_bias = max(0, 1.0 - abs(ref_progress - target_progress) * 2)
                score = calculate_similarity(ref.text, target.text)
                combined_score = score + (pos_bias * 0.05)
                
                if combined_score > max_score:
                    max_score = combined_score
                    current_best_match = target

        # 결과 저장
        if current_best_match is not None and max_score > 0.08: # 임계값 소폭 완화
            used_targets.add(current_best_match.index) # 사용 플래그 등록
            results.append({
                "matched": True,
                "translated": False,
                "ref_index": ref.index,
                "target_index": current_best_match.index,
                "ref": ref.to_dict(),
                "target": current_best_match.to_dict(),
                "score": round(float(max_score), 3),
                "new_start": ref.start,
                "new_end": ref.end
            })
            # 성공한 경우 위치 업데이트 (순차성 유지용)
            # 리스트 탐색 최적화
            for j in range(max(0, target_idx - 5), total_target):
                if target_subs[j].index == current_best_match.index:
                    target_idx = j
                    break
        else:
            results.append({
                "matched": False,
                "translated": False,
                "ref_index": ref.index,
                "target_index": None,
                "ref": ref.to_dict(),
                "target": None,
                "score": 0.0,
                "new_start": ref.start,
                "new_end": ref.end
            })
            
    matched_count = sum(1 for r in results if r['matched'])
    match_rate = matched_count / total_ref if total_ref > 0 else 0
    logger.info(f"자막 정합 1차 완료: {matched_count}/{total_ref} 매칭 성공 (매칭율: {match_rate:.1%}, 중복 재사용 방지 적용)")
    
    # [COMPLETED: 2026-04-11] 자막 매칭 임계값 30%로 조정 완료 (임의 수정 금지)
    if match_rate < 0.3:
        error_msg = f"자막 매칭율이 너무 낮습니다 ({match_rate:.1%}). 원본과 대상 자막의 내용이 서로 다르거나, 단순 번역 목적으로 의심되어 작업을 중단합니다. (최소 30% 필요)"
        logger.warning(error_msg)
        raise ValueError(error_msg)
    
    # 3. 누락된 자막 번역 보완 (지능형 갭 필러)
    if api_key:
        results = fill_missing_subtitles(results, api_key, ai_model, progress_callback=progress_callback, check_cancel=check_cancel, target_lang=target_lang)
    elif progress_callback:
        progress_callback(100)
        
    logger.info(f"최종 동기화 완료: 총 {len(results)}개 자막 산출")
    return results

if __name__ == "__main__":
    # 간단한 테스트 코드
    sample_ref = """1
00:00:01,000 --> 00:00:03,000
Hello World.
"""
    sample_target = """1
00:00:10,000 --> 00:00:12,000
안녕 세상. (Hello World)
"""
    ref_blocks = parse_srt(sample_ref)
    target_blocks = parse_srt(sample_target)
    aligned = align_subtitles(ref_blocks, target_blocks)
    for res in aligned:
        print(res)
