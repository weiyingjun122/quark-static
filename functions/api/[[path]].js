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

    // 路由到不同的处理函数
    switch (action) {
        case 'record':
            return await handleRecord(request, env, url, corsHeaders);
        case 'hot':
            return await handleHot(env, corsHeaders);
        case 'sync':
            return await handleSync(request, env, url, corsHeaders);
        case 'debug':
            return await handleDebug(request, env, corsHeaders);
        case 'health':
            return await handleHealth(corsHeaders);
        case 'ping':
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
}

// ============================================================
// 增强的 handleRecord 函数
// ============================================================
async function handleRecord(request, env, url, corsHeaders) {
    let keyword = '';
    let requestMethod = request.method;

    console.log(`收到 ${requestMethod} 请求到 /api/record`);

    // 根据请求方法获取关键词
    switch (requestMethod) {
        case 'GET':
            keyword = url.searchParams.get("q") || url.searchParams.get("keyword");
            break;

        case 'POST':
            try {
                const contentType = request.headers.get("content-type") || "";

                if (contentType.includes("application/json")) {
                    // JSON 格式
                    const body = await request.json();
                    keyword = body.keyword || body.q || body.query || body.search;
                } else if (contentType.includes("application/x-www-form-urlencoded")) {
                    // 表单格式
                    const formData = await request.formData();
                    keyword = formData.get("keyword") || formData.get("q");
                } else if (contentType.includes("text/plain")) {
                    // 纯文本
                    keyword = await request.text();
                } else {
                    // 尝试解析为 JSON
                    try {
                        const body = await request.json();
                        keyword = body.keyword;
                    } catch {
                        keyword = url.searchParams.get("q") || "";
                    }
                }
            } catch (error) {
                console.error("解析请求体失败:", error);
                return new Response(JSON.stringify({
                    success: false,
                    error: "Parse error",
                    message: "无法解析请求数据",
                    hint: "请使用: GET /api/record?q=关键词 或 POST with {'keyword':'关键词'}"
                }), {
                    status: 400,
                    headers: { "Content-Type": "application/json", ...corsHeaders }
                });
            }
            break;

        default:
            return new Response(JSON.stringify({
                success: false,
                error: "Method not allowed",
                allowed: ["GET", "POST"],
                usage: {
                    GET: "/api/record?q=关键词",
                    POST: '{"keyword":"关键词"}'
                }
            }), {
                status: 405,
                headers: { "Content-Type": "application/json", ...corsHeaders }
            });
    }

    // 验证关键词
    if (!keyword || keyword.trim() === "") {
        return new Response(JSON.stringify({
            success: false,
            error: "Missing keyword",
            received: { keyword, method: requestMethod },
            usage: {
                GET: "/api/record?q=电影",
                POST: 'curl -X POST -H "Content-Type: application/json" -d \'{"keyword":"电影"}\' /api/record'
            }
        }), {
            status: 400,
            headers: { "Content-Type": "application/json", ...corsHeaders }
        });
    }

    const normalizedKeyword = keyword.trim().toLowerCase();

    // 检查关键词长度
    if (normalizedKeyword.length > 100) {
        return new Response(JSON.stringify({
            success: false,
            error: "Keyword too long",
            maxLength: 100,
            receivedLength: normalizedKeyword.length
        }), {
            status: 400,
            headers: { "Content-Type": "application/json", ...corsHeaders }
        });
    }

    // 获取并更新统计
    let stats = {};
    try {
        const statsData = await env.SEARCH_STATS.get("stats");
        if (statsData) {
            stats = JSON.parse(statsData);
        }
    } catch (e) {
        console.error("读取 KV 失败:", e);
        stats = {};
    }

    // 更新计数
    const currentCount = (stats[normalizedKeyword] || 0) + 1;
    stats[normalizedKeyword] = currentCount;

    // 保存到 KV
    try {
        await env.SEARCH_STATS.put("stats", JSON.stringify(stats));
    } catch (e) {
        console.error("保存 KV 失败:", e);
        // 继续返回响应，即使保存失败
    }

    // 准备响应
    const responseData = {
        success: true,
        keyword: normalizedKeyword,
        count: currentCount,
        method: requestMethod,
        timestamp: new Date().toISOString(),
        isHot: currentCount >= 10,
        hotLevel: getHotLevel(currentCount)
    };

    return new Response(JSON.stringify(responseData), {
        headers: {
            "Content-Type": "application/json",
            ...corsHeaders,
            "Cache-Control": "no-store" // 不缓存统计响应
        }
    });
}

// 其他处理函数保持不变...

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
