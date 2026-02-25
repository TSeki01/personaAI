// ダッシュボード: 日本地図 + ペルソナパネル

const REGIONS = [
    { name: '北海道', prefs: ['北海道'] },
    { name: '東北', prefs: ['青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県'] },
    { name: '関東', prefs: ['茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県'] },
    { name: '中部', prefs: ['新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県'] },
    { name: '近畿', prefs: ['三重県', '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県'] },
    { name: '中国', prefs: ['鳥取県', '島根県', '岡山県', '広島県', '山口県'] },
    { name: '四国', prefs: ['徳島県', '香川県', '愛媛県', '高知県'] },
    { name: '九州・沖縄', prefs: ['福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県'] },
];

const REGION_COLORS = {
    '北海道': '#6c63ff',
    '東北': '#3b82f6',
    '関東': '#8b5cf6',
    '中部': '#06b6d4',
    '近畿': '#f59e0b',
    '中国': '#10b981',
    '四国': '#ec4899',
    '九州・沖縄': '#ef4444',
};

function buildMap() {
    const mapEl = document.getElementById('japan-map');
    if (!mapEl) return;

    mapEl.style.display = 'grid';
    mapEl.style.gridTemplateColumns = '1fr';
    mapEl.style.gap = '16px';

    REGIONS.forEach(region => {
        const section = document.createElement('div');
        section.className = 'region-group';

        const title = document.createElement('div');
        title.className = 'region-title';
        title.style.color = REGION_COLORS[region.name] || '#9097b5';
        title.textContent = `── ${region.name}`;
        section.appendChild(title);

        const chips = document.createElement('div');
        chips.className = 'prefecture-chips';

        region.prefs.forEach(pref => {
            const chip = document.createElement('button');
            chip.className = 'pref-chip';
            chip.textContent = pref;
            chip.dataset.pref = pref;
            chip.style.setProperty('--chip-color', REGION_COLORS[region.name] || '#6c63ff');
            chip.addEventListener('click', () => selectPrefecture(pref, chip));
            chips.appendChild(chip);
        });

        section.appendChild(chips);
        mapEl.appendChild(section);
    });
}
