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
    content = content.replace('\r\n', '\n').strip()
    raw_blocks = re.split(r'\n\s*\n', content)
    if len(raw_blocks) < 2:
        raw_blocks = re.split(r'\n(?=\d+\n\d{2}:\d{2}:\d{2})', "\n" + content)
    
    for raw in raw_blocks:
        lines = [l.strip() for l in raw.split('\n') if l.strip()]
        if len(lines) >= 3:
            try:
                idx_match = re.search(r'\d+', lines[0])
                if not idx_match: continue
                idx = int(idx_match.group())
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
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    blocks.append(SubtitleBlock(idx, start, end, text))
            except (ValueError, IndexError):
                continue
    return blocks

def parse_smi(content: str) -> List[SubtitleBlock]:
    blocks = []
    sync_points = re.findall(r'<SYNC Start=(\d+)>', content, re.IGNORECASE)
    contents = re.split(r'<SYNC Start=\d+>', content, flags=re.IGNORECASE)[1:]
    valid_blocks = []
    for i in range(len(sync_points)):
        start_ms = int(sync_points[i])
        text_raw = contents[i].strip()
        text = re.sub(r'<[^>]+>', ' ', text_raw, flags=re.IGNORECASE)
        text = re.sub(r'&nbsp;', ' ', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            end_ms = int(sync_points[i+1]) if i + 1 < len(sync_points) else start_ms + 3000
            valid_blocks.append(SubtitleBlock(len(valid_blocks) + 1, ms_to_srt_time(start_ms), ms_to_srt_time(end_ms), text))
    return valid_blocks

def parse_subtitles(content: str, filename: str = "") -> List[SubtitleBlock]:
    ext = filename.split('.')[-1].lower() if filename else ""
    if ext == 'smi' or '<SAMI>' in content.upper():
        return parse_smi(content)
    else:
        return parse_srt(content)

def calculate_similarity(text1: str, text2: str) -> float:
    t1 = re.sub(r'[^\w\s]', '', text1.lower())
    t2 = re.sub(r'[^\w\s]', '', text2.lower())
    words1 = set(t1.split())
    words2 = set(t2.split())
    text_score = 0.0
    if words1 and words2:
        intersection = words1.intersection(words2)
        text_score = len(intersection) / max(len(words1), len(words2))
    nums1 = set(re.findall(r'\d+', text1))
    nums2 = set(re.findall(r'\d+', text2))
    num_score = 0.0
    if nums1 and nums2:
        num_intersection = nums1.intersection(nums2)
        num_score = len(num_intersection) / max(len(nums1), len(nums2))
    punc1 = "".join(re.findall(r'[!?\.]{2,}', text1))
    punc2 = "".join(re.findall(r'[!?\.]{2,}', text2))
    punc_score = 0.5 if punc1 and punc1 == punc2 else 0.0
    len1 = len(text1.split())
    len2 = len(text2.split())
    len_ratio = min(len1, len2) / max(len1, len2) if max(len1, len2) > 0 else 0
    final_score = text_score * 1.0 + num_score * 0.8 + punc_score * 0.2
    if final_score == 0:
        final_score = len_ratio * 0.01 
    return final_score

def gemini_batch_match(ref_window: List[SubtitleBlock], target_window: List[SubtitleBlock], api_key: str, model_name: str = "gemini-3.1-flash-lite-preview") -> Dict:
    try:
        client = genai.Client(api_key=api_key)
        ref_data = [{"idx": b.index, "text": b.text} for b in ref_window]
        target_data = [{"idx": b.index, "text": b.text} for b in target_window]
        prompt = f"Match each Reference subtitle to the semantically equivalent Target subtitle.\nRef: {json.dumps(ref_data)}\nTarget: {json.dumps(target_data)}\nReturn JSON mapping Ref index to Target index."
        response = client.models.generate_content(
            model=model_name, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        usage = {}
        if response.usage_metadata:
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "candidates_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count
            }
        mapping = response.parsed
        if not mapping:
            raw_text = response.text.strip()
            if raw_text.startswith("```json"): raw_text = raw_text[7:]
            elif raw_text.startswith("```"): raw_text = raw_text[3:]
            if raw_text.endswith("```"): raw_text = raw_text[:-3]
            mapping = json.loads(raw_text.strip())
        return {"mapping": {int(k): v for k, v in mapping.items() if v is not None}, "usage": usage}
    except Exception as e:
        logger.error(f"Gemini API matching error: {str(e)}")
        return {"mapping": {}, "usage": {}}

def fill_missing_subtitles(results: List[Dict], api_key: str, model_name: str, progress_callback=None, check_cancel=None, target_lang: str="ko") -> Dict:
    lang_map = {"ko": "Korean", "en": "English", "ja": "Japanese", "zh": "Chinese", "hi": "Hindi", "es": "Spanish", "fr": "French", "de": "German"}
    target_lang_name = lang_map.get(target_lang, "Korean")
    total_usage = {"prompt_tokens": 0, "candidates_tokens": 0, "total_tokens": 0}
    try:
        client = genai.Client(api_key=api_key)
        missing_indices = [i for i, r in enumerate(results) if not r.get("matched", False)]
        if not missing_indices: return {"results": results, "usage": total_usage}
        matched_results = [r for r in results if r.get("matched", False) and not r.get("translated", False)]
        sample_size = min(20, len(matched_results))
        samples = []
        if sample_size > 0:
            step = max(1, len(matched_results) // sample_size)
            for i in range(0, len(matched_results), step):
                if len(samples) >= sample_size: break
                r = matched_results[i]
                samples.append({"original": r["ref"]["text"], "translated": r["target"]["text"]})
        batch_size = 30
        for i in range(0, len(missing_indices), batch_size):
            if check_cancel and check_cancel(): raise Exception("Cancelled")
            try:
                if progress_callback: progress_callback(80 + int((i / len(missing_indices)) * 20))
                batch_idxs = missing_indices[i:i + batch_size]
                batch_data = [{"id": idx, "text": results[idx]["ref"]["text"]} for idx in batch_idxs]
                prompt = f"Translate the following missing subtitles into {target_lang_name} based on samples.\nSamples: {json.dumps(samples)}\nData: {json.dumps(batch_data)}"
                response = client.models.generate_content(
                    model=model_name, contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                )
                if response.usage_metadata:
                    total_usage["prompt_tokens"] += response.usage_metadata.prompt_token_count
                    total_usage["candidates_tokens"] += response.usage_metadata.candidates_token_count
                    total_usage["total_tokens"] += response.usage_metadata.total_token_count
                mapping = response.parsed
                if not mapping:
                    raw_text = response.text.strip()
                    if raw_text.startswith("```json"): raw_text = raw_text[7:]
                    elif raw_text.startswith("```"): raw_text = raw_text[3:]
                    if raw_text.endswith("```"): raw_text = raw_text[:-3]
                    mapping = json.loads(raw_text.strip())
                for idx_str, translated_text in mapping.items():
                    idx_int = int(idx_str)
                    ref_info = results[idx_int]["ref"]
                    results[idx_int]["target"] = {"index": ref_info["index"], "start": ref_info["start"], "end": ref_info["end"], "text": translated_text}
                    results[idx_int]["target_index"] = ref_info["index"]
                    results[idx_int]["matched"] = True
                    results[idx_int]["translated"] = True
                    results[idx_int]["score"] = 1.0
                time.sleep(0.5)
            except Exception as batch_e:
                logger.error(f"Gemini translation error: {str(batch_e)}")
                continue
    except Exception as e:
        logger.error(f"Gemini translation setup error: {str(e)}")
    if progress_callback: progress_callback(100)
    return {"results": results, "usage": total_usage}

def align_subtitles(ref_subs: List[SubtitleBlock], target_subs: List[SubtitleBlock], api_key: Optional[str] = None, ai_model: str = "gemini-3.1-flash-lite-preview", progress_callback=None, check_cancel=None, target_lang: str = "ko") -> Dict:
    results = []
    total_ref = len(ref_subs)
    total_target = len(target_subs)
    target_map = {s.index: s for s in target_subs}
    used_targets = set()
    total_usage = {"prompt_tokens": 0, "candidates_tokens": 0, "total_tokens": 0}
    
    ai_mapping: Dict[int, int] = {}
    if api_key:
        batch_size = 30
        for i in range(0, total_ref, batch_size):
            if check_cancel and check_cancel(): raise Exception("Cancelled")
            if progress_callback: progress_callback(max(5, int((i / max(total_ref, 1)) * 60)))
            ref_batch = ref_subs[i:i + batch_size]
            progress = i / total_ref
            approx_target_idx = int(progress * total_target)
            target_range = target_subs[max(0, approx_target_idx - 50):min(total_target, approx_target_idx + 100)]
            batch_res = gemini_batch_match(ref_batch, target_range, api_key, ai_model)
            ai_mapping.update(batch_res.get("mapping", {}))
            u = batch_res.get("usage", {})
            total_usage["prompt_tokens"] += u.get("prompt_tokens", 0)
            total_usage["candidates_tokens"] += u.get("candidates_tokens", 0)
            total_usage["total_tokens"] += u.get("total_tokens", 0)
            time.sleep(0.5) 
            
    target_idx = 0
    for idx, ref in enumerate(ref_subs):
        if check_cancel and idx % 20 == 0 and check_cancel(): raise Exception("Cancelled")
        if progress_callback and idx % 20 == 0:
            base_p = 60 if api_key else 0
            remaining_p = 20 if api_key else 80
            progress_callback(base_p + int((idx / max(total_ref, 1)) * remaining_p))
        current_best_match = None
        max_score = 0.0
        if ref.index in ai_mapping:
            matched_idx = ai_mapping[ref.index]
            if matched_idx in target_map and matched_idx not in used_targets:
                current_best_match = target_map[matched_idx]
                max_score = 1.0 
        if current_best_match is None:
            ref_progress = idx / total_ref if total_ref > 0 else 0
            for i in range(max(0, target_idx - 20), min(total_target, target_idx + 40)):
                target = target_subs[i]
                if target.index in used_targets: continue
                target_progress = i / total_target if total_target > 0 else 0
                pos_bias = max(0, 1.0 - abs(ref_progress - target_progress) * 2)
                score = calculate_similarity(ref.text, target.text)
                combined_score = score + (pos_bias * 0.05)
                if combined_score > max_score:
                    max_score = combined_score
                    current_best_match = target
        if current_best_match is not None and max_score > 0.08:
            used_targets.add(current_best_match.index)
            results.append({"matched": True, "translated": False, "ref_index": ref.index, "target_index": current_best_match.index, "ref": ref.to_dict(), "target": current_best_match.to_dict(), "score": round(float(max_score), 3), "new_start": ref.start, "new_end": ref.end})
            for j in range(max(0, target_idx - 5), total_target):
                if target_subs[j].index == current_best_match.index:
                    target_idx = j
                    break
        else:
            results.append({"matched": False, "translated": False, "ref_index": ref.index, "target_index": None, "ref": ref.to_dict(), "target": None, "score": 0.0, "new_start": ref.start, "new_end": ref.end})
            
    matched_count = sum(1 for r in results if r['matched'])
    match_rate = matched_count / total_ref if total_ref > 0 else 0
    if match_rate < 0.3: raise ValueError(f"자막 매칭율이 너무 낮습니다 ({match_rate:.1%}). 최소 30% 필요.")
    
    if api_key:
        fill_res = fill_missing_subtitles(results, api_key, ai_model, progress_callback=progress_callback, check_cancel=check_cancel, target_lang=target_lang)
        results = fill_res["results"]
        u = fill_res.get("usage", {})
        total_usage["prompt_tokens"] += u.get("prompt_tokens", 0)
        total_usage["candidates_tokens"] += u.get("candidates_tokens", 0)
        total_usage["total_tokens"] += u.get("total_tokens", 0)
    elif progress_callback:
        progress_callback(100)
    return {"results": results, "usage": total_usage}
