export async function onRequestPost(context) {
  try {
    const { request, env } = context;
    const body = await request.json();
    const keyword = body.keyword?.trim();

    if (!keyword) {
      return new Response(JSON.stringify({ error: "关键词不能为空" }), {
        status: 400
      });
    }

    const issueTitle = `求资源：${keyword}`;

    // 1️⃣ 先查询是否已有相同 Issue
    const searchRes = await fetch(
      `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/issues?state=open&per_page=100`,
      {
        headers: {
          Authorization: `Bearer ${env.GITHUB_TOKEN}`,
          Accept: "application/vnd.github+json"
        }
      }
    );

    const issues = await searchRes.json();
    const existing = issues.find(i => i.title === issueTitle);

    if (existing) {
      // 2️⃣ 已存在 → 评论 +1
      await fetch(existing.comments_url, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.GITHUB_TOKEN}`,
          Accept: "application/vnd.github+json"
        },
        body: JSON.stringify({
          body: "👍 又有一位用户求此资源"
        })
      });

      return new Response(JSON.stringify({ message: "已增加热度" }), {
        status: 200
      });
    }

    // 3️⃣ 不存在 → 创建新 Issue
    await fetch(
      `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/issues`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.GITHUB_TOKEN}`,
          Accept: "application/vnd.github+json"
        },
        body: JSON.stringify({
          title: issueTitle,
          body: `用户求资源关键词：${keyword}`
        })
      }
    );

    return new Response(JSON.stringify({ message: "提交成功" }), {
      status: 200
    });

  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500
    });
  }
}
