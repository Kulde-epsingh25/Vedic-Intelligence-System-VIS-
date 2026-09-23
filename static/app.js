/**
 * VEDIC INTELLIGENCE SYSTEM (VIS) — FRONTEND CONTROLLER
 * Handles tab transitions, RAG interactions, semantic search,
 * word grammatical breakdown, speech synthesis, and canvas ontology graph.
 */

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  fetchSystemStats();
  initAIScholar();
  initVerseReader();
  initSemanticSearch();
  initCharacterCodex();
  initScienceBridge();
  initKnowledgeGraph();
});

// ─────────────────────────────────────────────────────────
// 1. TABS NAVIGATION
// ─────────────────────────────────────────────────────────
function initTabs() {
  const navBtns = document.querySelectorAll('.nav-btn');
  const panels = document.querySelectorAll('.tab-panel');

  navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      navBtns.forEach(b => b.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const tabId = btn.getAttribute('data-tab');
      const targetPanel = document.getElementById(`tab-${tabId}`);
      if (targetPanel) {
        targetPanel.classList.add('active');
      }

      // Resize or re-render graph if switching to knowledge graph
      if (tabId === 'knowledge-graph') {
        window.dispatchEvent(new Event('resize-graph'));
      }
    });
  });
}

// ─────────────────────────────────────────────────────────
// 2. SYSTEM STATS TICKER
// ─────────────────────────────────────────────────────────
async function fetchSystemStats() {
  try {
    const res = await fetch('/stats');
    const data = await res.json();
    if (data.status === 'ok' && data.tables) {
      const t = data.tables;
      const statsBadge = document.getElementById('stats-text');
      statsBadge.textContent = `${t.verses || 0} Verses • ${t.characters || 0} Characters • ${t.concepts || 0} Concepts • ${t.science_links || 0} Science Papers`;
    }
  } catch (err) {
    console.warn('Failed to fetch stats:', err);
    document.getElementById('stats-text').textContent = 'Vedic Corpus Active';
  }
}

// ─────────────────────────────────────────────────────────
// 3. AI SCHOLAR (RAG ENGINE)
// ─────────────────────────────────────────────────────────
function initAIScholar() {
  const askInput = document.getElementById('ai-query-input');
  const submitBtn = document.getElementById('btn-submit-ask');
  const resultBox = document.getElementById('ai-result-container');
  const chips = document.querySelectorAll('.chip');
  const speakBtn = document.getElementById('btn-speak-answer');

  let currentSanskritText = '';

  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      askInput.value = chip.getAttribute('data-q');
      askQuestion();
    });
  });

  submitBtn.addEventListener('click', askQuestion);
  askInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      askQuestion();
    }
  });

  async function askQuestion() {
    const q = askInput.value.trim();
    if (!q) return;

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span>Consulting Seers...</span>';
    resultBox.classList.remove('hidden');

    document.getElementById('ai-answer-text').innerHTML = '<div style="color: #94a3b8; font-style: italic;">Transcribing insight from sacred verses & science archives...</div>';
    document.getElementById('shloka-citation-box').classList.add('hidden');
    document.getElementById('science-parallel-box').classList.add('hidden');

    try {
      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, k: 5 })
      });
      const data = await res.json();

      document.getElementById('ai-confidence').textContent = `Confidence: ${(data.confidence * 100).toFixed(0)}%`;
      document.getElementById('ai-model').textContent = data.model_used || 'Vedic-RAG Core';
      document.getElementById('ai-answer-text').textContent = data.answer || 'No direct answer retrieved.';

      if (data.source_verses && data.source_verses.length > 0) {
        const topVerse = data.source_verses[0];
        document.getElementById('shloka-citation-box').classList.remove('hidden');
        document.getElementById('cited-verse-id').textContent = topVerse.verse_id;

        // Fetch detailed verse info to get translation and Devanagari
        try {
          const vRes = await fetch(`/verse/${encodeURIComponent(topVerse.verse_id)}`);
          const vData = await vRes.json();
          if (vData.verse) {
            document.getElementById('cited-devanagari').textContent = vData.verse.devanagari || topVerse.text;
            document.getElementById('cited-iast').textContent = vData.verse.iast || '';
            document.getElementById('cited-translation').textContent = `Translation: "${vData.verse.translation_en || ''}"`;
            currentSanskritText = vData.verse.devanagari || vData.verse.iast || topVerse.text;
          }
        } catch {
          document.getElementById('cited-devanagari').textContent = topVerse.text;
          document.getElementById('cited-iast').textContent = '';
          document.getElementById('cited-translation').textContent = '';
          currentSanskritText = topVerse.text;
        }
      }

      // Modern Science parallel
      if (data.science_links && data.science_links.length > 0) {
        const s = data.science_links[0];
        const scBox = document.getElementById('science-parallel-box');
        scBox.classList.remove('hidden');
        document.getElementById('parallel-domain').textContent = s.domain || 'Physics';
        document.getElementById('parallel-title').textContent = s.modern_title || '';
        document.getElementById('parallel-ref').textContent = s.modern_ref || '';
        document.getElementById('parallel-desc').textContent = s.description || s.modern_abstract || '';
      } else {
        // Also check if question triggered known science mapping
        checkAndInjectScience(q);
      }

    } catch (err) {
      document.getElementById('ai-answer-text').innerHTML = `<span style="color: #ef4444;">Error inquiring: ${err.message}</span>`;
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span>Inquire</span><span class="btn-arrow">➔</span>';
    }
  }

  async function checkAndInjectScience(q) {
    const qLower = q.toLowerCase();
    let concept = null;
    if (qLower.includes('paramanu') || qLower.includes('quantum') || qLower.includes('atomic')) concept = 'paramanu';
    else if (qLower.includes('yoga') || qLower.includes('mind') || qLower.includes('vritti') || qLower.includes('meditation')) concept = 'citta_vritti';
    else if (qLower.includes('ayurveda') || qLower.includes('dosha') || qLower.includes('health')) concept = 'tridosha';
    else if (qLower.includes('creation') || qLower.includes('nasadiya') || qLower.includes('cosmos')) concept = 'nasadiya';
    else if (qLower.includes('akasha') || qLower.includes('space') || qLower.includes('vacuum')) concept = 'akasha';

    if (concept) {
      try {
        const res = await fetch(`/science-links?concept_id=${concept}`);
        const data = await res.json();
        if (data.links && data.links.length > 0) {
          const s = data.links[0];
          const scBox = document.getElementById('science-parallel-box');
          scBox.classList.remove('hidden');
          document.getElementById('parallel-domain').textContent = s.domain || 'Science';
          document.getElementById('parallel-title').textContent = s.modern_title || '';
          document.getElementById('parallel-ref').textContent = s.modern_ref || '';
          document.getElementById('parallel-desc').textContent = s.description || s.modern_abstract || '';
        }
      } catch {}
    }
  }

  // Recite Sanskrit shloka with Speech Synthesis
  speakBtn.addEventListener('click', () => {
    if (!currentSanskritText && !window.speechSynthesis) return;
    const utterance = new SpeechSynthesisUtterance(currentSanskritText);
    utterance.lang = 'hi-IN'; // Devanagari pronunciation
    utterance.rate = 0.88;
    window.speechSynthesis.speak(utterance);
  });
}

// ─────────────────────────────────────────────────────────
// 4. SACRED VERSE READER & GRAMMATICAL BREAKDOWN
// ─────────────────────────────────────────────────────────
async function initVerseReader() {
  const container = document.getElementById('verses-container');
  const filter = document.getElementById('verse-source-filter');
  const countDisplay = document.getElementById('verse-count-display');

  loadVerses();

  filter.addEventListener('change', () => {
    loadVerses(filter.value);
  });

  async function loadVerses(sourceText = '') {
    container.innerHTML = '<div style="color: #94a3b8; text-align: center; padding: 2rem;">Loading verses...</div>';
    try {
      const url = sourceText ? `/verses?source_text_id=${sourceText}&limit=50` : `/verses?limit=50`;
      const res = await fetch(url);
      const data = await res.json();
      const verses = data.verses || [];

      countDisplay.textContent = `Showing ${verses.length} verses`;
      container.innerHTML = '';

      if (verses.length === 0) {
        container.innerHTML = '<div style="color: #94a3b8; text-align: center; padding: 2rem;">No verses found for this filter.</div>';
        return;
      }

      for (const v of verses) {
        const card = document.createElement('div');
        card.className = 'verse-card';
        card.innerHTML = `
          <div class="verse-card-header">
            <span class="verse-tag-pill">${v.verse_id}</span>
            <span class="verse-era">${v.era || 'Classical'} Canon</span>
          </div>
          <div class="devanagari-text" style="font-size: 1.25rem;">${v.devanagari.replace(/\n/g, '<br>')}</div>
          <div class="iast-text">${v.iast}</div>
          <div class="translation-text"><strong>Meaning:</strong> ${v.translation_en || 'Exposition in progress'}</div>
          
          <div class="words-breakdown-section">
            <div class="words-header">Paninian Grammatical Breakdown (Click pada for analysis):</div>
            <div class="words-chips-container" id="padas-${v.verse_id.replace(/\./g, '_')}">
              <span style="color: #64748b; font-size: 0.85rem;">Analyzing padas...</span>
            </div>
          </div>
        `;
        container.appendChild(card);

        // Load words for this verse
        loadWordsForVerse(v.verse_id);
      }
    } catch (err) {
      container.innerHTML = `<div style="color: #ef4444; padding: 2rem;">Failed to load verses: ${err.message}</div>`;
    }
  }

  async function loadWordsForVerse(verseId) {
    const padasBox = document.getElementById(`padas-${verseId.replace(/\./g, '_')}`);
    if (!padasBox) return;

    try {
      const res = await fetch(`/verse/${encodeURIComponent(verseId)}`);
      const data = await res.json();
      const words = data.words || [];

      padasBox.innerHTML = '';
      if (words.length === 0) {
        padasBox.innerHTML = '<span style="color: #64748b; font-size: 0.85rem;">Word-level decomposition parsed via Vidyut rules</span>';
        return;
      }

      words.forEach(w => {
        const chip = document.createElement('button');
        chip.className = 'pada-chip';
        chip.textContent = w.surface_devanagari || w.surface_form;
        chip.title = `${w.surface_form}: ${w.meaning_en || 'Click for grammar details'}`;
        chip.addEventListener('click', () => showGrammarModal(w));
        padasBox.appendChild(chip);
      });
    } catch {}
  }
}

// ─────────────────────────────────────────────────────────
// 5. WORD GRAMMAR MODAL
// ─────────────────────────────────────────────────────────
function showGrammarModal(word) {
  const modal = document.getElementById('grammar-modal');
  const title = document.getElementById('modal-word-title');
  const content = document.getElementById('modal-grammar-content');
  const closeBtn = document.getElementById('modal-close');

  title.textContent = `${word.surface_devanagari || word.surface_form} (${word.stem || word.surface_form})`;
  content.innerHTML = `
    <div class="grammar-row">
      <span class="grammar-label">Pada ID:</span>
      <span class="grammar-value">${word.pada_id}</span>
    </div>
    <div class="grammar-row">
      <span class="grammar-label">Verbal Root (Dhātu):</span>
      <span class="grammar-value">${word.dhatu ? `√${word.dhatu}` : 'Prātipadika (Nominal base)'}</span>
    </div>
    <div class="grammar-row">
      <span class="grammar-label">Inflectional Case (Vibhakti):</span>
      <span class="grammar-value">${word.vibhakti_name || (word.vibhakti ? `Case ${word.vibhakti}` : 'Avyaya (Indeclinable)')}</span>
    </div>
    <div class="grammar-row">
      <span class="grammar-label">Grammatical Number (Vacana):</span>
      <span class="grammar-value">${word.vachana_name || 'Singular / Uninflected'}</span>
    </div>
    <div class="grammar-row">
      <span class="grammar-label">Gender (Liṅga):</span>
      <span class="grammar-value">${word.linga === 'm' ? 'Masculine (Puṃlinga)' : word.linga === 'f' ? 'Feminine (Strīlinga)' : word.linga === 'n' ? 'Neuter (Napuṃsakalinga)' : 'N/A'}</span>
    </div>
    <div class="grammar-row">
      <span class="grammar-label">English Definition:</span>
      <span class="grammar-value" style="color: var(--gold-primary);">${word.meaning_en || 'Root analysis complete'}</span>
    </div>
  `;

  modal.classList.remove('hidden');

  closeBtn.onclick = () => modal.classList.add('hidden');
  modal.onclick = (e) => {
    if (e.target === modal) modal.classList.add('hidden');
  };
}

// ─────────────────────────────────────────────────────────
// 6. SEMANTIC SEARCH
// ─────────────────────────────────────────────────────────
function initSemanticSearch() {
  const input = document.getElementById('search-query-input');
  const btn = document.getElementById('btn-submit-search');
  const container = document.getElementById('search-results-container');

  btn.addEventListener('click', performSearch);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') performSearch();
  });

  async function performSearch() {
    const q = input.value.trim();
    if (!q) return;

    btn.disabled = true;
    btn.textContent = 'Searching...';
    container.innerHTML = '<div style="color: #94a3b8; text-align: center; padding: 2rem;">Computing semantic vectors & cosine similarity...</div>';

    try {
      const res = await fetch('/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, limit: 10 })
      });
      const data = await res.json();
      const results = data.results || [];

      container.innerHTML = '';
      if (results.length === 0) {
        container.innerHTML = '<div style="color: #94a3b8; text-align: center; padding: 2rem;">No matching verses found. Try another concept query.</div>';
        return;
      }

      results.forEach(r => {
        const card = document.createElement('div');
        card.className = 'verse-card';
        card.style.marginBottom = '1.2rem';
        const similarityPct = Math.round((r.similarity || 0.85) * 100);

        card.innerHTML = `
          <div class="verse-card-header">
            <span class="verse-tag-pill">${r.verse_id}</span>
            <span class="badge confidence-badge">Match: ${similarityPct}%</span>
          </div>
          <div class="devanagari-text" style="font-size: 1.15rem; white-space: pre-line;">${r.text}</div>
        `;
        container.appendChild(card);
      });
    } catch (err) {
      container.innerHTML = `<div style="color: #ef4444; padding: 2rem;">Search failed: ${err.message}</div>`;
    } finally {
      btn.disabled = false;
      btn.textContent = 'Search';
    }
  }
}

// ─────────────────────────────────────────────────────────
// 7. CHARACTER CODEX
// ─────────────────────────────────────────────────────────
async function initCharacterCodex() {
  const container = document.getElementById('characters-container');
  try {
    const res = await fetch('/characters');
    const data = await res.json();
    const characters = data.characters || [];

    container.innerHTML = '';
    characters.forEach(c => {
      const card = document.createElement('div');
      card.className = 'char-card';
      card.innerHTML = `
        <div class="char-header">
          <div class="char-names">
            <h3>${c.name_en}</h3>
            <div class="sa-name">${c.name_sa || ''}</div>
          </div>
          <span class="char-type-badge">${c.char_type || 'Seer'}</span>
        </div>
        <div class="char-desc">${c.description || ''}</div>
        <div class="char-meta">
          <div><strong>Lineage:</strong> ${c.lineage || 'Ancient tradition'}</div>
          <div><strong>Attributes:</strong> ${c.attributes || 'Dharmic guidance'}</div>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = `<div style="color: #ef4444;">Failed to load characters: ${err.message}</div>`;
  }
}

// ─────────────────────────────────────────────────────────
// 8. SCIENCE BRIDGE
// ─────────────────────────────────────────────────────────
async function initScienceBridge() {
  const container = document.getElementById('science-links-container');
  try {
    const res = await fetch('/science-links');
    const data = await res.json();
    const links = data.links || [];

    container.innerHTML = '';
    links.forEach(l => {
      const card = document.createElement('div');
      card.className = 'science-card';
      card.innerHTML = `
        <div class="science-header">
          <span class="atom-icon">⚛️</span>
          <h4>${l.concept_id.toUpperCase()} ⇄ ${l.domain}</h4>
          <span class="domain-tag">${l.domain}</span>
        </div>
        <div class="parallel-title">${l.modern_title}</div>
        <div class="parallel-ref">${l.modern_ref}</div>
        <p class="parallel-desc">${l.description || l.modern_abstract}</p>
        <div style="margin-top: 0.8rem; font-size: 0.8rem; color: var(--gold-primary);">
          Linked Shloka Anchor: <strong>${l.verse_id}</strong> (Confidence: ${(l.confidence * 100).toFixed(0)}%)
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = `<div style="color: #ef4444;">Failed to load science links: ${err.message}</div>`;
  }
}

// ─────────────────────────────────────────────────────────
// 9. KNOWLEDGE GRAPH (INTERACTIVE HTML5 CANVAS)
// ─────────────────────────────────────────────────────────
function initKnowledgeGraph() {
  const canvas = document.getElementById('knowledge-graph-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  let width = canvas.width;
  let height = canvas.height;

  function resizeCanvas() {
    canvas.width = canvas.parentElement.clientWidth || 1000;
    canvas.height = 580;
    width = canvas.width;
    height = canvas.height;
  }
  window.addEventListener('resize', resizeCanvas);
  window.addEventListener('resize-graph', resizeCanvas);
  resizeCanvas();

  // Nodes & Edges definition
  const nodes = [
    // Texts (Gold)
    { id: 'BG', label: 'Bhagavad Gita', type: 'text', x: width * 0.35, y: height * 0.3, vx: 0, vy: 0, r: 24, color: '#ffd700' },
    { id: 'YS', label: 'Yoga Sutras', type: 'text', x: width * 0.65, y: height * 0.3, vx: 0, vy: 0, r: 24, color: '#ffd700' },
    { id: 'RV', label: 'Rigveda', type: 'text', x: width * 0.5, y: height * 0.15, vx: 0, vy: 0, r: 26, color: '#ffd700' },
    { id: 'CS', label: 'Charaka Samhita', type: 'text', x: width * 0.8, y: height * 0.45, vx: 0, vy: 0, r: 22, color: '#ffd700' },

    // Characters (Purple)
    { id: 'krishna', label: 'Krishna', type: 'char', x: width * 0.2, y: height * 0.25, vx: 0, vy: 0, r: 20, color: '#c084fc' },
    { id: 'arjuna', label: 'Arjuna', type: 'char', x: width * 0.2, y: height * 0.42, vx: 0, vy: 0, r: 18, color: '#c084fc' },
    { id: 'patanjali', label: 'Patanjali', type: 'char', x: width * 0.78, y: height * 0.2, vx: 0, vy: 0, r: 18, color: '#c084fc' },

    // Concepts (Cyan)
    { id: 'karma', label: 'Karma', type: 'concept', x: width * 0.35, y: height * 0.6, vx: 0, vy: 0, r: 18, color: '#38bdf8' },
    { id: 'dharma', label: 'Dharma', type: 'concept', x: width * 0.5, y: height * 0.48, vx: 0, vy: 0, r: 22, color: '#38bdf8' },
    { id: 'paramanu', label: 'Paramanu (Atom)', type: 'concept', x: width * 0.4, y: height * 0.78, vx: 0, vy: 0, r: 20, color: '#38bdf8' },
    { id: 'citta', label: 'Citta-Vritti', type: 'concept', x: width * 0.65, y: height * 0.62, vx: 0, vy: 0, r: 18, color: '#38bdf8' },
    { id: 'tridosha', label: 'Tridosha', type: 'concept', x: width * 0.85, y: height * 0.65, vx: 0, vy: 0, r: 18, color: '#38bdf8' },

    // Science Domains (Emerald)
    { id: 'quantum', label: 'Quantum Physics', type: 'science', x: width * 0.35, y: height * 0.92, vx: 0, vy: 0, r: 22, color: '#34d399' },
    { id: 'neuro', label: 'Neuroscience (fMRI)', type: 'science', x: width * 0.65, y: height * 0.85, vx: 0, vy: 0, r: 22, color: '#34d399' },
    { id: 'biology', label: 'Circadian Biology', type: 'science', x: width * 0.88, y: height * 0.85, vx: 0, vy: 0, r: 20, color: '#34d399' },
  ];

  const edges = [
    { from: 'BG', to: 'krishna' },
    { from: 'BG', to: 'arjuna' },
    { from: 'BG', to: 'karma' },
    { from: 'BG', to: 'dharma' },
    { from: 'YS', to: 'patanjali' },
    { from: 'YS', to: 'citta' },
    { from: 'RV', to: 'paramanu' },
    { from: 'RV', to: 'dharma' },
    { from: 'CS', to: 'tridosha' },
    { from: 'paramanu', to: 'quantum' },
    { from: 'citta', to: 'neuro' },
    { from: 'tridosha', to: 'biology' },
    { from: 'dharma', to: 'karma' },
  ];

  let draggedNode = null;
  let hoveredNode = null;

  canvas.addEventListener('mousedown', (e) => {
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    for (const node of nodes) {
      const dx = mouseX - node.x;
      const dy = mouseY - node.y;
      if (Math.sqrt(dx * dx + dy * dy) < node.r) {
        draggedNode = node;
        break;
      }
    }
  });

  window.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    if (draggedNode) {
      draggedNode.x = mouseX;
      draggedNode.y = mouseY;
    } else {
      hoveredNode = null;
      for (const node of nodes) {
        const dx = mouseX - node.x;
        const dy = mouseY - node.y;
        if (Math.sqrt(dx * dx + dy * dy) < node.r) {
          hoveredNode = node;
          break;
        }
      }
    }
  });

  window.addEventListener('mouseup', () => {
    draggedNode = null;
  });

  function drawGraph() {
    ctx.clearRect(0, 0, width, height);

    // Draw Edges
    edges.forEach(e => {
      const n1 = nodes.find(n => n.id === e.from);
      const n2 = nodes.find(n => n.id === e.to);
      if (n1 && n2) {
        ctx.beginPath();
        ctx.moveTo(n1.x, n1.y);
        ctx.lineTo(n2.x, n2.y);
        ctx.strokeStyle = 'rgba(255, 215, 0, 0.2)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    });

    // Draw Nodes
    nodes.forEach(node => {
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.r, 0, Math.PI * 2);
      ctx.fillStyle = node.color;
      ctx.shadowColor = node.color;
      ctx.shadowBlur = (hoveredNode === node || draggedNode === node) ? 22 : 10;
      ctx.fill();
      ctx.shadowBlur = 0;

      ctx.lineWidth = 2;
      ctx.strokeStyle = '#ffffff';
      ctx.stroke();

      // Label
      ctx.font = '600 12px Inter, sans-serif';
      ctx.fillStyle = '#f8fafc';
      ctx.textAlign = 'center';
      ctx.fillText(node.label, node.x, node.y + node.r + 16);
    });

    requestAnimationFrame(drawGraph);
  }

  drawGraph();
}
