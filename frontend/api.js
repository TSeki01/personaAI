// API通信の共通モジュール
// 本番: <script data-api-url="https://persona-api.onrender.com"> でURLを注入
// 開発: 自動でlocalhost:8000を使用
const _scriptEl = document.currentScript || document.querySelector('script[data-api-url]');
const API_BASE = (_scriptEl && _scriptEl.dataset.apiUrl) || 'http://127.0.0.1:8000';


async function fetchPersonas(prefecture = null, region = null) {
  const params = new URLSearchParams();
  if (prefecture) params.append('prefecture', prefecture);
  if (region) params.append('region', region);
  const res = await fetch(`${API_BASE}/api/personas?${params}`);
  return res.json();
}

async function fetchPersona(id) {
  const res = await fetch(`${API_BASE}/api/personas/${encodeURIComponent(id)}`);
  return res.json();
}

async function fetchPersonaProfile(id) {
  const res = await fetch(`${API_BASE}/api/personas/${encodeURIComponent(id)}/profile`);
  if (!res.ok) throw new Error('プロファイルの取得に失敗しました');
  return res.json();
}

async function enhancePersonaProfile(id) {
  const res = await fetch(`${API_BASE}/api/personas/${encodeURIComponent(id)}/profile/enhance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail || '';
    if (res.status === 429) throw new Error('APIの無料枠上限に達しました。しばらく待ってください。');
    throw new Error(`エラー: ${detail}`);
  }
  return res.json();
}

async function fetchPrefectures() {
  const res = await fetch(`${API_BASE}/api/prefectures`);
  return res.json();
}

async function fetchUsage() {
  const res = await fetch(`${API_BASE}/api/usage`);
  return res.json();
}

async function sendInterview(personaId, message, history) {
  const res = await fetch(`${API_BASE}/api/interview/${encodeURIComponent(personaId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail || JSON.stringify(err);
    if (res.status === 429 || (detail && detail.includes('RESOURCE_EXHAUSTED'))) {
      throw new Error('APIの無料枠の上限に達しました。しばらく待ってから再試行してください（1分〜数時間）。');
    }
    throw new Error(`サーバーエラー (${res.status}): ${detail}`);
  }
  return res.json();
}

function streamBulkQuestion(question, prefectureFilter, onProgress, onDone, onError) {
  const params = new URLSearchParams({ question });
  if (prefectureFilter) params.append('prefecture_filter', prefectureFilter);

  const evtSource = new EventSource(`${API_BASE}/api/bulk-question?${params}`, {
    withCredentials: false,
  });

  evtSource.addEventListener('progress', (e) => {
    onProgress(JSON.parse(e.data));
  });
  evtSource.addEventListener('done', () => {
    evtSource.close();
    onDone();
  });
  evtSource.addEventListener('error', (e) => {
    evtSource.close();
    onError(e);
  });
  return evtSource;
}

// ── ただしSSEはGETが前提なのでbulk-questionをGETに変更する
// main.pyのエンドポイントもGETに対応させる必要がある
// → bulk.jsでfetch+ReadableStreamを使う方式に切り替え

async function* streamBulkQuestionFetch(question, prefectureFilter) {
  const body = { question };
  if (prefectureFilter) body.prefecture_filter = prefectureFilter;

  const res = await fetch(`${API_BASE}/api/bulk-question`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();
    for (const line of lines) {
      if (line.startsWith('data:')) {
        const data = line.slice(5).trim();
        if (data) {
          try { yield JSON.parse(data); } catch { }
        }
      }
    }
  }
}

function getGenderEmoji(gender) {
  return gender === '男性' ? '👨' : '👩';
}

function getPoliticalColor(leaning) {
  if (leaning.includes('自民') || leaning.includes('公明')) return '#ef4444';
  if (leaning.includes('立憲') || leaning.includes('共産')) return '#3b82f6';
  if (leaning.includes('維新')) return '#f59e0b';
  return '#6b7280';
}
