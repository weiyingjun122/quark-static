// functions/api/[[path]].js
export async function onRequest(context) {
    const { request, env } = context;
    const url = new URL(request.url);
    const pathSegments = url.pathname.split('/').filter(Boolean);

    // 只处理 /api/ 开头的请求
    if (pathSegments[0] !== 'api') {
        return new Response('Not Found', { status: 404 });
    }

    const action = pathSegments[1]; // record, hot, sync, debug, health
    const subAction = pathSegments[2]; // 如果有三级路径

    // CORS 配置
    const corsHeaders = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "86400",
    };

    // 处理 OPTIONS 预检请求
    if (request.method === "OPTIONS") {
        return new Response(null, { headers: corsHeaders });
    }

    try {
        switch (action) {
            case 'record':
                return await handleRecord(request, env, url, corsHeaders);
            case 'hot':
                return await handleHot(env, corsHeaders);
            case 'sync':
                return await handleSync(url, env, corsHeaders);
            case 'debug':
                return await handleDebug(request, env, corsHeaders);
            case 'health':
                return await handleHealth(corsHeaders);
            case 'ping':
            case 'status':
                return await handlePing(corsHeaders);
            default:
                return new Response(JSON.stringify({
                    error: "Endpoint not found",
                    available: ["/api/record", "/api/hot", "/api/sync", "/api/debug", "/api/health", "/api/ping"]
                }), {
                    status: 404,
                    headers: { "Content-Type": "application/json", ...corsHeaders }
                });
        }
    } catch (error) {
        console.error('API Error:', error);
        return new Response(JSON.stringify({
            error: "Internal server error",
            message: error.message
        }), {
            status: 500,
            headers: { "Content-Type": "application/json", ...corsHeaders }
        });
    }
}

// ============================================================
// 各个处理函数
// ============================================================

// 处理记录搜索
async function handleRecord(request, env, url, corsHeaders) {
    const keyword = url.searchParams.get("q");

    if (!keyword || keyword.trim() === "") {
        return new Response(JSON.stringify({
            success: false,
            error: "Missing keyword"
        }), {
            status: 400,
            headers: { "Content-Type": "application/json", ...corsHeaders }
        });
    }

    // 从 KV 获取统计
    let stats = {};
    try {
        const statsData = await env.SEARCH_STATS.get("stats");
        if (statsData) {
            stats = JSON.parse(statsData);
        }
    } catch (e) {
        stats = {};
    }

    // 更新统计
    const normalizedKeyword = keyword.trim().toLowerCase();
    stats[normalizedKeyword] = (stats[normalizedKeyword] || 0) + 1;

    // 保存到 KV
    try {
        await env.SEARCH_STATS.put("stats", JSON.stringify(stats));
    } catch (e) {
        console.error("KV save error:", e);
    }

    return new Response(JSON.stringify({
        success: true,
        keyword: normalizedKeyword,
        count: stats[normalizedKeyword],
        timestamp: Date.now()
    }), {
        headers: { "Content-Type": "application/json", ...corsHeaders }
    });
}

// 处理热搜
async function handleHot(env, corsHeaders) {
    let stats = {};
    try {
        const statsData = await env.SEARCH_STATS.get("stats");
        if (statsData) {
            stats = JSON.parse(statsData);
        }
    } catch (e) {
        stats = {};
    }

    const THRESHOLD = 10;
    const hotList = Object.entries(stats)
    .filter(([_, count]) => count >= THRESHOLD)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([word, count]) => ({
        word,
        count,
        isHot: count >= 50,
        level: getHotLevel(count)
    }));

    return new Response(JSON.stringify(hotList), {
        headers: { "Content-Type": "application/json", ...corsHeaders }
    });
}

// 处理同步
async function handleSync(url, env, corsHeaders) {
    const secret = url.searchParams.get("key");

    if (secret !== "my_secret_sync_key") {
        return new Response("Unauthorized", {
            status: 401,
            headers: { "Content-Type": "text/plain" }
        });
    }

    let stats = {};
    try {
        const statsData = await env.SEARCH_STATS.get("stats");
        if (statsData) {
            stats = JSON.parse(statsData);
        }
    } catch (e) {
        stats = {};
    }

    const THRESHOLD = 10;
    const filteredStats = {};

    Object.entries(stats).forEach(([word, count]) => {
        if (count >= THRESHOLD) {
            filteredStats[word] = count;
        }
    });

    const sortedEntries = Object.entries(filteredStats)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 50);

    const result = Object.fromEntries(sortedEntries);

    return new Response(JSON.stringify(result), {
        headers: { "Content-Type": "application/json" } // sync不需要CORS
    });
}

// 处理调试
async function handleDebug(request, env, corsHeaders) {
    let stats = {};
    try {
        const statsData = await env.SEARCH_STATS.get("stats");
        if (statsData) {
            stats = JSON.parse(statsData);
        }
    } catch (e) {
        stats = {};
    }

    const THRESHOLD = 10;
    const allStats = Object.entries(stats)
    .sort((a, b) => b[1] - a[1])
    .map(([word, count]) => ({
        word,
        count,
        meetsThreshold: count >= THRESHOLD
    }));

    const statsSummary = {
        totalKeywords: Object.keys(stats).length,
        totalSearches: Object.values(stats).reduce((sum, count) => sum + count, 0),
        threshold: THRESHOLD,
        keywordsAboveThreshold: allStats.filter(item => item.meetsThreshold).length,
        averageSearchesPerKeyword: Object.keys(stats).length > 0
        ? (Object.values(stats).reduce((sum, count) => sum + count, 0) / Object.keys(stats).length).toFixed(2)
        : "0.00",
        topKeywords: allStats.slice(0, 10)
    };

    return new Response(JSON.stringify({
        debug: true,
        summary: statsSummary,
        allStats: allStats,
        timestamp: new Date().toISOString()
    }, null, 2), {
        headers: { "Content-Type": "application/json", ...corsHeaders }
    });
}

// 处理健康检查
async function handleHealth(corsHeaders) {
    return new Response(JSON.stringify({
        status: "healthy",
        service: "quark-search-api",
        timestamp: new Date().toISOString(),
                                       endpoints: [
                                           "/api/record",
                                           "/api/hot",
                                           "/api/sync",
                                           "/api/debug",
                                           "/api/health"
                                       ]
    }), {
        headers: { "Content-Type": "application/json", ...corsHeaders }
    });
}

// 处理 ping
async function handlePing(corsHeaders) {
    return new Response(JSON.stringify({
        pong: Date.now(),
                                       timestamp: new Date().toISOString()
    }), {
        headers: { "Content-Type": "application/json", ...corsHeaders }
    });
}

// 辅助函数
function getHotLevel(count) {
    if (count >= 100) return "🔥🔥🔥";
    if (count >= 50) return "🔥🔥";
    if (count >= 20) return "🔥";
    if (count >= 10) return "👍";
    return "📊";
}
