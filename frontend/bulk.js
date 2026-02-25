// 一括質問ページロジック
let allResults = [];
let isRunning = false;
let currentStream = null;
let timerInterval = null;
let startTime = null;

const RPM_LIMIT = 15; // gemini_client.py の設定値と履いておく

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function estimatedSeconds(personaCount) {
    return Math.ceil(personaCount / RPM_LIMIT) * 60;
}

function updateEstLabel() {
    const sel = document.getElementById('pref-filter');
    const val = sel ? sel.value : '';
    const label = document.getElementById('est-time-label');
    if (!label) return;
    if (!val) {
        label.textContent = '⏱ 所要時間の目安：約31分（全470人）';
    } else {
        // 都道府県フィルター時は10人
        label.textContent = '⏱ 所要時間の目安：約1分以内（10人対象）';
    }
}

async function initBulk() {
    // 都道府県フィルターの選択肢を構築
    try {
        const data = await fetchPrefectures();
        const sel = document.getElementById('pref-filter');
        const selResult = document.getElementById('region-filter-result');

        Object.keys(data.prefectures).sort().forEach(pref => {
            const opt = document.createElement('option');
            opt.value = pref;
            opt.textContent = `${pref}（10人）`;
            sel.appendChild(opt);
        });

        if (data.regions) {
            Object.keys(data.regions).forEach(region => {
                const opt = document.createElement('option');
                opt.value = region;
                opt.textContent = region;
                selResult.appendChild(opt);
            });
        }

        const total = Object.values(data.prefectures).reduce((a, b) => a + b, 0);
        document.getElementById('total-count').textContent = total;

        // フィルター変更時に目安時間更新
        const prefSel = document.getElementById('pref-filter');
        if (prefSel) prefSel.addEventListener('change', updateEstLabel);
    } catch (e) {
        console.error('初期化エラー:', e);
    }
}

async function startBulkQuestion() {
    const question = document.getElementById('question-input').value.trim();
    if (!question) { alert('質問を入力してください'); return; }
    if (isRunning) return;

    const prefFilter = document.getElementById('pref-filter').value;
    isRunning = true;
    allResults = [];

    // UIリセット
    const btn = document.getElementById('ask-btn');
    btn.disabled = true;
    document.getElementById('ask-btn-text').textContent = '⏳ 質問中...';
    document.getElementById('results-grid').innerHTML = '';
    document.getElementById('results-area').style.display = 'none';
    document.getElementById('elapsed-time').textContent = '0:00';
    document.getElementById('remaining-time').textContent = '--:--';

    // タイマー開始
    startTime = Date.now();
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
        const elapsed = (Date.now() - startTime) / 1000;
        document.getElementById('elapsed-time').textContent = formatTime(elapsed);
    }, 1000);

    // 進捗カード表示
    const progressCard = document.getElementById('progress-card');
    progressCard.style.display = 'block';
    progressCard.scrollIntoView({ behavior: 'smooth' });

    const progressBar = document.getElementById('progress-bar');
    const progressCount = document.getElementById('progress-count');
    const progressStatus = document.getElementById('progress-status');

    try {
        for await (const item of streamBulkQuestionFetch(question, prefFilter || null)) {
            if (item.event === 'done' || item.total === undefined) continue;

            const pct = (item.completed / item.total * 100).toFixed(1);
            progressBar.style.width = pct + '%';
            progressCount.textContent = `${item.completed} / ${item.total}`;
            progressStatus.textContent = `最新: ${item.persona_name}（${item.prefecture}）が回答しました`;

            allResults.push(item);
            appendResultCard(item);

            // 初回回答時に总数から残り時間を計算
            if (item.completed === 1) {
                document.getElementById('results-area').style.display = 'block';
                const estSec = estimatedSeconds(item.total);
                // 毎秒更新
                clearInterval(timerInterval);
                timerInterval = setInterval(() => {
                    const elapsed = (Date.now() - startTime) / 1000;
                    const remaining = Math.max(0, estSec - elapsed);
                    document.getElementById('elapsed-time').textContent = formatTime(elapsed);
                    document.getElementById('remaining-time').textContent = remaining > 0 ? formatTime(remaining) : '完了';
                }, 1000);
            }
            document.getElementById('result-count').textContent = allResults.length + '件';
        }
    } catch (e) {
        progressStatus.textContent = `エラー: ${e.message}`;
        console.error(e);
    }

    // 完了
    clearInterval(timerInterval);
    const elapsed = (Date.now() - startTime) / 1000;
    document.getElementById('elapsed-time').textContent = formatTime(elapsed);
    document.getElementById('remaining-time').textContent = '完了';
    progressStatus.textContent = `✅ 全${allResults.length}人の回答が完了しました！`;
    btn.disabled = false;
    document.getElementById('ask-btn-text').textContent = '📡 全員に質問する';
    isRunning = false;
}

function appendResultCard(item) {
    const grid = document.getElementById('results-grid');
    const card = document.createElement('div');
    card.className = 'result-card';
    card.dataset.region = item.region || '';
    card.dataset.answer = (item.answer || '').toLowerCase();
    card.dataset.pref = item.prefecture || '';
    card.innerHTML = `
    <div class="result-card-header">
      <div class="result-avatar">${getGenderEmoji(item.gender)}</div>
      <div class="result-meta">
        <div class="result-name">${item.age}歳 ${item.gender}・${item.occupation}</div>
        <div class="result-occ">${item.persona_id}</div>
      </div>
      <span class="result-pref-tag">${item.prefecture}</span>
    </div>
    <div class="result-text">${escapeHtml(item.answer)}</div>
  `;
    grid.appendChild(card);
}

function filterResults() {
    const search = (document.getElementById('search-input').value || '').toLowerCase();
    const region = document.getElementById('region-filter-result').value;
    const cards = document.querySelectorAll('.result-card');
    let visible = 0;
    cards.forEach(card => {
        const matchSearch = !search || card.dataset.answer.includes(search) || card.dataset.pref.includes(search);
        const matchRegion = !region || card.dataset.region === region;
        const show = matchSearch && matchRegion;
        card.style.display = show ? '' : 'none';
        if (show) visible++;
    });
    document.getElementById('result-count').textContent = visible + '件';
}

function escapeHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

initBulk();
