export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const target = url.searchParams.get("target");
    const adId = url.searchParams.get("ad_id") || "unknown";

    if (url.pathname === "/click" && target) {
      // TODO: 추후 env.AD_STATS.put(adId, count) 등을 이용해 통계 누적
      console.log(`[Ad Click Event] ID: ${adId}, Timestamp: ${new Date().toISOString()}`);

      // 리다이렉션을 발생시켜 원래 광고 페이지로 라우팅
      return Response.redirect(target, 302);
    }
    
    return new Response("SubFast Web Tracker Running", { status: 200 });
  }
};
