// 허용할 도메인 목록 (서비스 도메인 + 로컬 개발 환경)
// contact-api.mainko.net은 Worker 엔드포인트로 사용 (CORS Origin은 호출자의 도메인)
const ALLOWED_ORIGINS = [
  'https://subtitle.mainko.net',
  'http://localhost:5173',
  'http://localhost:4173', // vite preview
];

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const isAllowed = ALLOWED_ORIGINS.includes(origin);

    // 허용된 Origin에만 CORS 헤더를 반환, 아니면 빈 값
    const corsHeaders = {
      'Access-Control-Allow-Origin': isAllowed ? origin : '',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    // OPTIONS preflight 요청 처리
    if (request.method === 'OPTIONS') {
      // 허용되지 않은 Origin의 preflight는 403 반환
      if (!isAllowed) {
        return new Response(null, { status: 403 });
      }
      return new Response(null, { headers: corsHeaders });
    }

    // 허용되지 않은 Origin의 본 요청은 403 차단
    if (!isAllowed) {
      return new Response(JSON.stringify({ error: 'Forbidden: Origin not allowed' }), {
        status: 403,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (request.method !== 'POST') {
      return new Response(JSON.stringify({ error: 'Method not allowed' }), {
        status: 405,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    try {
      const data = await request.json();
      const { name, email, type, message } = data;

      if (!name || !email || !type || !message) {
        return new Response(JSON.stringify({ error: 'Missing required fields' }), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }

      // Telegram Bot Token & Chat ID는 Worker Secret 환경변수에서 안전하게 불러옴
      // 클라이언트(브라우저)에는 절대 노출되지 않음
      const botToken = env.TELEGRAM_BOT_TOKEN;
      const chatId = env.TELEGRAM_CHAT_ID;

      if (!botToken || !chatId) {
        return new Response(JSON.stringify({ error: 'Telegram credentials not configured on server' }), {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }

      const text = [
        `📨 [SubMaster 문의/협찬]`,
        `━━━━━━━━━━━━━━━━━━`,
        `👤 이름: ${name}`,
        `📧 이메일: ${email}`,
        `📂 유형: ${type}`,
        `━━━━━━━━━━━━━━━━━━`,
        `💬 내용:\n${message}`,
      ].join('\n');

      const telegramRes = await fetch(
        `https://api.telegram.org/bot${botToken}/sendMessage`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chat_id: chatId, text }),
        }
      );

      if (!telegramRes.ok) {
        const errBody = await telegramRes.text();
        return new Response(JSON.stringify({ error: 'Telegram API error', details: errBody }), {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }

      return new Response(JSON.stringify({ success: true, message: 'Message sent via Telegram!' }), {
        status: 200,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });

    } catch (err) {
      return new Response(JSON.stringify({ error: 'Internal Server Error', message: err.message }), {
        status: 500,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }
  },
};
