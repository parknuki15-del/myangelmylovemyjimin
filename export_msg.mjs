/* 把留言板云端表里的纸条全部导出来，存成一份 JSON。
   只用 REST，不依赖 SDK —— 环境还活着就能读到。
   注意：读策略是「公开的 + 自己藏的」，这里的匿名身份是全新的，
   所以别人设为「只给自己看」的纸条**读不到**（这是对的，不该被导出）。 */

const ENV_ID = 'jimin-board-d4g6tai3ode672bf0';
const ROOT = `https://${ENV_ID}.api.tcloudbasegateway.com`;
const ORIGIN = 'https://myangelmylovemyjimin.com';

// 1. 匿名登录拿 token
const DEVICE = 'export-' + Math.random().toString(36).slice(2, 12);
const r1 = await fetch(`${ROOT}/auth/v1/signin/anonymously`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Origin: ORIGIN,
    'x-device-id': DEVICE,
    'x-device-type': 'web',
    'x-version': '1.0.0'
  },
  body: '{}'
});
const t1 = await r1.json().catch(() => null);
if (r1.status !== 200) {
  console.error('❌ 匿名登录失败 HTTP ' + r1.status);
  console.error(JSON.stringify(t1, null, 2).slice(0, 800));
  process.exit(1);
}
const token = t1.access_token || (t1.session && t1.session.access_token);
const uid = (t1.user && t1.user.id) || (t1.session && t1.session.user && t1.session.user.id);
console.log('✅ 已登录匿名身份 ' + uid);

// 2. 读表
async function get(cols) {
  const url = `${ROOT}/v1/rdb/rest/messages?select=${cols}&order=created_at.asc&limit=2000`;
  const r = await fetch(url, {
    headers: {
      Authorization: 'Bearer ' + token,
      'Content-Type': 'application/json',
      Origin: ORIGIN,
      'Accept-Language': 'zh-CN'
    }
  });
  let body = null;
  try { body = await r.json(); } catch (e) {}
  return { status: r.status, body };
}

let res = await get('id,name,text,time,created_at,user_id,hidden');
if (res.status !== 200) {
  console.log('（带 hidden 读失败 HTTP ' + res.status + '，可能是没有这一列 → 退回普通读取）');
  res = await get('id,name,text,time,created_at,user_id');
}

if (res.status !== 200) {
  console.error('❌ 读表失败 HTTP ' + res.status);
  console.error(JSON.stringify(res.body, null, 2).slice(0, 1200));
  process.exit(1);
}

const rows = Array.isArray(res.body) ? res.body
           : (Array.isArray(res.body && res.body.data) ? res.body.data : []);
console.log('✅ 读到 ' + rows.length + ' 张纸条');

const out = process.argv[2] || '/tmp/messages-export.json';
const fs = await import('fs');
fs.writeFileSync(out, JSON.stringify({ envId: ENV_ID, exportedAt: new Date().toISOString(), count: rows.length, rows }, null, 2));
console.log('已写入 ' + out);

// 3. 顺便在终端打一份，肉眼能核
console.log('\n---- 纸条清单（按写入时间正序）----');
rows.forEach((x, i) => {
  console.log(
    String(i + 1).padStart(3) +
    '  [' + (x.time || '') + ']  ' +
    (x.name || '(匿名)') + '：' +
    String(x.text || '').replace(/\s+/g, ' ').slice(0, 60) +
    (x.hidden ? '   <隐藏>' : '')
  );
});
