// ダッシュボードページロジック
let personaCache = {}; // prefecture -> [Persona]
let profileCache = {}; // persona_id -> PersonaProfile
let selectedChip = null;
let currentPersonaId = null;

async function init() {
  buildMap();
  try {
    // 軽量エンドポイントでカウントだけ取得
    const data = await fetchPrefectures();
    const total = Object.values(data.prefectures).reduce((a, b) => a + b, 0);
    document.getElementById('total-count').textContent = total;
  } catch (e) {
    document.getElementById('total-count').textContent = 'エラー';
    console.error('API接続エラー:', e);
  }
  updateUsage();
  setInterval(updateUsage, 10000); // 10秒ごとに更新
}

async function updateUsage() {
  try {
    const u = await fetchUsage();
    const bar = document.getElementById('usage-bar');
    const count = document.getElementById('usage-count');
    const rpm = document.getElementById('usage-rpm');
    const remain = document.getElementById('usage-remain');
    if (!bar) return;
    bar.style.width = u.quota_pct_used + '%';
    // 残量が少なくなったら赤色に変化
    const color = u.quota_pct_used > 80 ? 'var(--red)' : u.quota_pct_used > 50 ? 'var(--yellow)' : 'var(--green)';
    bar.style.background = color;
    count.textContent = `${u.requests_today}/${u.rpd_limit}`;
    rpm.textContent = u.rpm_current;
    remain.textContent = u.requests_remaining_today;
    remain.style.color = u.requests_remaining_today < 100 ? 'var(--red)' : 'var(--green)';
  } catch { }
}

function selectPrefecture(pref, chip) {
  // チップの選択状態切り替え
  document.querySelectorAll('.pref-chip').forEach(c => c.classList.remove('selected'));
  if (selectedChip === pref) {
    selectedChip = null;
    closePanel();
    return;
  }
  chip.classList.add('selected');
  selectedChip = pref;
  showPersonasForPref(pref);
}

async function showPersonasForPref(pref) {
  const panel = document.getElementById('persona-panel');
  const grid = document.getElementById('persona-grid');
  const title = document.getElementById('panel-title');

  title.textContent = `${pref}のペルソナ（読込中...）`;
  grid.innerHTML = '<div style="color:var(--text3);padding:20px">読み込み中...</div>';
  panel.style.display = 'block';
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  // キャッシュがあれば再利用
  if (!personaCache[pref]) {
    const data = await fetchPersonas(pref);
    personaCache[pref] = data.personas;
  }
  const personas = personaCache[pref];

  title.textContent = `${pref}のペルソナ（${personas.length}人）`;
  grid.innerHTML = '';
  personas.forEach(p => {
    const card = createPersonaCard(p);
    grid.appendChild(card);
  });
}

function createPersonaCard(p) {
  const div = document.createElement('div');
  div.className = 'persona-card';
  div.onclick = () => openModal(p);
  div.innerHTML = `
    <div class="card-avatar">${getGenderEmoji(p.gender)}</div>
    <div class="card-name">${p.age}歳・${p.gender}</div>
    <div class="card-sub">${p.occupation}</div>
    <div class="card-tags">
      <span class="tag">年収${p.annual_income}万円</span>
      <span class="tag">${p.household_type}</span>
      <span class="tag political">${p.political_leaning}</span>
    </div>
  `;
  return div;
}

// ── モーダル: 3タブ構成 ────────────────────────────────────────────
function openModal(persona) {
  currentPersonaId = persona.id;
  const content = document.getElementById('modal-content');

  content.innerHTML = `
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px">
      <div style="width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#6c63ff,#a78bfa);display:flex;align-items:center;justify-content:center;font-size:26px">${getGenderEmoji(persona.gender)}</div>
      <div>
        <div style="font-size:18px;font-weight:700">${persona.age}歳 ${persona.gender}</div>
        <div style="font-size:13px;color:var(--text2)">${persona.prefecture} / ${persona.region}</div>
      </div>
    </div>
    <div class="modal-tabs">
      <button class="modal-tab active" id="tab-profile" onclick="switchTab('profile')">👤 プロフィール</button>
      <button class="modal-tab" id="tab-lifelog" onclick="switchTab('lifelog')">📖 経歴</button>
      <button class="modal-tab" id="tab-psych" onclick="switchTab('psych')">🧠 心理</button>
    </div>
    <div id="tab-content-profile" class="tab-content active">${buildProfileHtml(persona)}</div>
    <div id="tab-content-lifelog" class="tab-content">
      <div style="color:var(--text3);padding:20px;text-align:center">⏳ 読み込み中...</div>
    </div>
    <div id="tab-content-psych" class="tab-content">
      <div style="color:var(--text3);padding:20px;text-align:center">⏳ 読み込み中...</div>
    </div>
  `;

  document.getElementById('interview-btn').onclick = () => {
    window.location.href = `interview.html?id=${persona.id}`;
  };

  const overlay = document.getElementById('modal-overlay');
  overlay.classList.add('open');

  // プロファイルを非同期でロード
  loadProfileTabs(persona.id);
}

async function loadProfileTabs(personaId) {
  if (profileCache[personaId]) {
    renderProfileTabs(profileCache[personaId]);
    return;
  }
  try {
    const profile = await fetchPersonaProfile(personaId);
    profileCache[personaId] = profile;
    renderProfileTabs(profile);
  } catch (e) {
    const errHtml = `<div style="color:var(--red);padding:16px">プロファイルの読み込みに失敗: ${e.message}</div>`;
    const lg = document.getElementById('tab-content-lifelog');
    const ps = document.getElementById('tab-content-psych');
    if (lg) lg.innerHTML = errHtml;
    if (ps) ps.innerHTML = errHtml;
  }
}

function renderProfileTabs(profile) {
  const lgEl = document.getElementById('tab-content-lifelog');
  const psEl = document.getElementById('tab-content-psych');
  if (lgEl) lgEl.innerHTML = buildLifelogHtml(profile.lifelog);
  if (psEl) psEl.innerHTML = buildPsychHtml(profile.psych);
}

function switchTab(tab) {
  document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById(`tab-${tab}`).classList.add('active');
  document.getElementById(`tab-content-${tab}`).classList.add('active');
}

function buildProfileHtml(persona) {
  const traits = persona.personality_traits.join('・');
  return `
    <div class="profile-section">
      <h3>仕事・収入</h3>
      <div class="profile-row"><span>職業</span><span>${persona.occupation}</span></div>
      <div class="profile-row"><span>年収</span><span>${persona.annual_income}万円</span></div>
      <div class="profile-row"><span>雇用形態</span><span>${persona.employment_type}</span></div>
    </div>
    <div class="profile-section">
      <h3>生活</h3>
      <div class="profile-row"><span>世帯構成</span><span>${persona.household_type}</span></div>
      <div class="profile-row"><span>住居</span><span>${persona.housing}</span></div>
      <div class="profile-row"><span>月の食費</span><span>${persona.monthly_food.toLocaleString()}円</span></div>
      <div class="profile-row"><span>月の住居費</span><span>${persona.monthly_housing.toLocaleString()}円</span></div>
      <div class="profile-row"><span>月の娯楽費</span><span>${persona.monthly_entertainment.toLocaleString()}円</span></div>
      <div class="profile-row"><span>通勤時間</span><span>${persona.commute_minutes}分</span></div>
    </div>
    <div class="profile-section">
      <h3>価値観</h3>
      <div class="profile-row"><span>政治的傾向</span><span>${persona.political_leaning}</span></div>
      <div class="profile-row"><span>性格</span><span>${traits}</span></div>
    </div>
    <div class="profile-section">
      <h3>日常</h3>
      <p style="font-size:13px;color:var(--text2);line-height:1.8">${persona.daily_routine}</p>
    </div>
  `;
}

// カテゴリアイコン
const CATEGORY_ICON = { education: '🎓', work: '💼', family: '👨‍👩‍👧', residence: '🏠' };

function buildLifelogHtml(events) {
  if (!events || events.length === 0) return '<div style="color:var(--text3);padding:16px">データなし</div>';
  const items = events.map(e => `
    <div class="timeline-item">
      <div class="timeline-dot ${e.category}"></div>
      <div class="timeline-body">
        <div class="timeline-year">${e.year}年 <span class="tl-age">（${e.age}歳）</span></div>
        <div class="timeline-event">${CATEGORY_ICON[e.category] || '📌'} ${e.event}</div>
      </div>
    </div>
  `).join('');
  return `<div class="timeline">${items}</div>`;
}

function buildPsychHtml(psych) {
  if (!psych) return '<div style="color:var(--text3);padding:16px">データなし</div>';
  const anxietyTags = psych.future_anxiety.map(a => `<span class="psych-tag anxiety">${a}</span>`).join('');
  const habitItems = psych.lifestyle_habits.map(h => `<li>${h}</li>`).join('');
  const infoItems = psych.info_sources.map(s => `<span class="psych-tag info">${s}</span>`).join('');
  const snsItems = Object.entries(psych.sns_usage).map(([k, v]) => `
    <div class="profile-row"><span>${k}</span><span class="sns-usage">${v}</span></div>
  `).join('');

  return `
    <div class="profile-section">
      <h3>💭 内面・悩み</h3>
      <div class="profile-row"><span>生活満足度</span></div>
      <p style="font-size:13px;color:var(--text2);line-height:1.7;margin:4px 0 10px">${psych.life_satisfaction}</p>
      <div class="profile-row"><span>将来の不安</span></div>
      <div style="margin:6px 0 10px;display:flex;flex-wrap:wrap;gap:6px">${anxietyTags}</div>
      <div class="profile-row"><span>仕事観</span></div>
      <p style="font-size:13px;color:var(--text2);line-height:1.7;margin:4px 0">${psych.work_values}</p>
    </div>
    <div class="profile-section">
      <h3>🔄 習慣・変化</h3>
      <ul style="font-size:13px;color:var(--text2);line-height:1.9;padding-left:18px;margin:0 0 10px">${habitItems}</ul>
      <div class="profile-row"><span>価値観の変遷</span></div>
      <p style="font-size:13px;color:var(--text2);line-height:1.7;margin:4px 0">${psych.values_shift}</p>
    </div>
    <div class="profile-section">
      <h3>📱 情報収集</h3>
      ${snsItems}
      <div class="profile-row" style="margin-top:8px"><span>メディア信頼</span></div>
      <p style="font-size:13px;color:var(--text2);line-height:1.7;margin:4px 0 10px">${psych.media_trust}</p>
      <div class="profile-row"><span>主な情報源</span></div>
      <div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:6px">${infoItems}</div>
    </div>
  `;
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
}

function closePanel() {
  document.getElementById('persona-panel').style.display = 'none';
}

init();


