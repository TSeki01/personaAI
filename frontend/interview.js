// インタビューページロジック
let personaId = null;
let persona = null;
let personaProfile = null;
let chatHistory = [];

async function initInterview() {
  const params = new URLSearchParams(window.location.search);
  personaId = params.get('id');
  if (!personaId) { window.location.href = 'index.html'; return; }

  try {
    persona = await fetchPersona(personaId);
    renderProfile(persona);
    updateChatHeader(persona);
    // プロファイル（ライフログ・心理）を非同期でロード
    fetchPersonaProfile(personaId).then(profile => {
      personaProfile = profile;
      renderProfileAccordion(profile);
    }).catch(() => { /* サイレントフェイル */ });
  } catch (e) {
    document.getElementById('profile-content').textContent = 'ペルソナの読み込みに失敗しました';
    console.error(e);
  }
}

function renderProfile(p) {
  const el = document.getElementById('profile-content');
  const traits = p.personality_traits.join('・');
  el.innerHTML = `
    <div style="text-align:center;margin-bottom:20px">
      <div style="width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,#6c63ff,#a78bfa);display:flex;align-items:center;justify-content:center;font-size:30px;margin:0 auto 10px">${getGenderEmoji(p.gender)}</div>
      <div style="font-size:16px;font-weight:700">${p.age}歳 ${p.gender}</div>
      <div style="font-size:12px;color:var(--text2)">${p.prefecture}</div>
    </div>
    <div class="profile-section">
      <h3>仕事・収入</h3>
      <div class="profile-row"><span>職業</span><span>${p.occupation}</span></div>
      <div class="profile-row"><span>年収</span><span>${p.annual_income}万円</span></div>
    </div>
    <div class="profile-section">
      <h3>生活</h3>
      <div class="profile-row"><span>世帯</span><span>${p.household_type}</span></div>
      <div class="profile-row"><span>住居</span><span>${p.housing}</span></div>
      <div class="profile-row"><span>通勤</span><span>${p.commute_minutes}分</span></div>
      <div class="profile-row"><span>食費/月</span><span>${p.monthly_food.toLocaleString()}円</span></div>
      <div class="profile-row"><span>娯楽費/月</span><span>${p.monthly_entertainment.toLocaleString()}円</span></div>
    </div>
    <div class="profile-section">
      <h3>価値観</h3>
      <div class="profile-row"><span>政治</span><span>${p.political_leaning}</span></div>
      <div class="profile-row"><span>性格</span><span>${traits}</span></div>
    </div>
    <div class="profile-section">
      <h3>日常</h3>
      <p style="font-size:12px;color:var(--text2);line-height:1.8">${p.daily_routine}</p>
    </div>
    <div id="profile-accordion-area"></div>
  `;
}

function renderProfileAccordion(profile) {
  const area = document.getElementById('profile-accordion-area');
  if (!area) return;

  // ライフログアコーディオン
  const lifelogItems = profile.lifelog.map(e => {
    const icons = { education: '🎓', work: '💼', family: '👨‍👩‍👧', residence: '🏠' };
    return `<div class="acc-tl-item">
            <span class="acc-tl-year">${e.year}</span>
            <span class="acc-tl-event">${icons[e.category] || '📌'} ${e.event}</span>
        </div>`;
  }).join('');

  // 心理プロファイルアコーディオン
  const ps = profile.psych;
  const anxietyTags = ps.future_anxiety.map(a => `<span class="psych-tag anxiety">${a}</span>`).join('');
  const infoTags = ps.info_sources.map(s => `<span class="psych-tag info">${s}</span>`).join('');

  area.innerHTML = `
    <div class="accordion">
      <button class="accordion-btn" onclick="toggleAccordion(this)">📖 経歴 <span class="acc-arrow">▼</span></button>
      <div class="accordion-body">
        <div class="acc-timeline">${lifelogItems}</div>
      </div>
    </div>
    <div class="accordion">
      <button class="accordion-btn" onclick="toggleAccordion(this)">🧠 心理プロファイル <span class="acc-arrow">▼</span></button>
      <div class="accordion-body">
        <div style="font-size:11px;color:var(--text2);line-height:1.7;margin-bottom:8px">${ps.life_satisfaction}</div>
        <div style="margin-bottom:6px;font-size:11px;font-weight:600;color:var(--text3)">将来の不安</div>
        <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px">${anxietyTags}</div>
        <div style="font-size:11px;color:var(--text2);line-height:1.6;margin-bottom:8px">${ps.values_shift}</div>
        <div style="margin-bottom:6px;font-size:11px;font-weight:600;color:var(--text3)">情報源</div>
        <div style="display:flex;flex-wrap:wrap;gap:4px">${infoTags}</div>
      </div>
    </div>
  `;
}

function toggleAccordion(btn) {
  const body = btn.nextElementSibling;
  const arrow = btn.querySelector('.acc-arrow');
  const isOpen = body.style.maxHeight;
  body.style.maxHeight = isOpen ? '' : body.scrollHeight + 'px';
  arrow.style.transform = isOpen ? '' : 'rotate(180deg)';
}

function updateChatHeader(p) {
  document.getElementById('chat-avatar').textContent = getGenderEmoji(p.gender);
  document.getElementById('chat-name').textContent = `${p.prefecture}の${p.age}歳 ${p.gender}`;
  document.getElementById('chat-sub').textContent = p.occupation;
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text || !personaId) return;

  input.value = '';
  const btn = document.getElementById('send-btn');
  btn.disabled = true;

  // ユーザーメッセージ追加
  appendMessage('user', text, '🧑');

  // タイピングインジケーター
  const typingEl = appendTyping();

  try {
    const result = await sendInterview(personaId, text, chatHistory);
    typingEl.remove();
    appendMessage('persona', result.answer, getGenderEmoji(persona.gender));

    // 履歴に追加
    chatHistory.push({ role: 'user', content: text });
    chatHistory.push({ role: 'model', content: result.answer });
  } catch (e) {
    typingEl.remove();
    appendMessage('persona', `（エラーが発生しました: ${e.message}）`, '⚠️');
  }

  btn.disabled = false;
  input.focus();
}

function appendMessage(role, text, avatarEmoji) {
  const container = document.getElementById('chat-messages');
  const notice = container.querySelector('.chat-notice');
  if (notice) notice.remove();

  const msg = document.createElement('div');
  msg.className = `message ${role}`;
  msg.innerHTML = `
    <div class="msg-avatar">${avatarEmoji}</div>
    <div class="msg-bubble">${escapeHtml(text).replace(/\n/g, '<br>')}</div>
  `;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
  return msg;
}

function appendTyping() {
  const container = document.getElementById('chat-messages');
  const msg = document.createElement('div');
  msg.className = 'message persona';
  msg.innerHTML = `
    <div class="msg-avatar">${persona ? getGenderEmoji(persona.gender) : '🤔'}</div>
    <div class="msg-bubble">
      <div class="msg-typing">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
  return msg;
}

function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function escapeHtml(str) {
  return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

initInterview();
