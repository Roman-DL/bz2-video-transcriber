/**
 * Topaz-Nord Color Scheme for n8n Workflow
 * Exact configuration from user's Blue Topaz settings
 * Theme: topaz-nord | Callout Style: border-callout-style
 */

// ========================================
// CALLOUT STYLES (Border Style)
// ========================================

const CALLOUT_STYLES = {
  'note': {
    emoji: '📝',
    title: 'Заметка',
    rgb: '8, 109, 221',
    hex: '#086DDD'
  },
  'abstract': {
    emoji: '📄',
    title: 'Резюме',
    rgb: '0, 176, 255',
    hex: '#00B0FF'
  },
  'info': {
    emoji: 'ℹ️',
    title: 'Информация',
    rgb: '0, 184, 212',
    hex: '#00B8D4'
  },
  'todo': {
    emoji: '✅',
    title: 'Задача',
    rgb: '0, 184, 212',
    hex: '#00B8D4'
  },
  'tip': {
    emoji: '💡',
    title: 'Совет',
    rgb: '0, 191, 165',
    hex: '#00BFA5'
  },
  'success': {
    emoji: '✔️',
    title: 'Успех',
    rgb: '0, 200, 83',
    hex: '#00C853'
  },
  'question': {
    emoji: '❓',
    title: 'Вопрос',
    rgb: '100, 221, 23',
    hex: '#64DD17'
  },
  'warning': {
    emoji: '⚠️',
    title: 'Внимание',
    rgb: '255, 145, 0',
    hex: '#FF9100'
  },
  'failure': {
    emoji: '❌',
    title: 'Ошибка',
    rgb: '255, 82, 82',
    hex: '#FF5252'
  },
  'danger': {
    emoji: '⛔',
    title: 'Опасно',
    rgb: '255, 23, 68',
    hex: '#FF1744'
  },
  'bug': {
    emoji: '🐛',
    title: 'Баг',
    rgb: '245, 0, 87',
    hex: '#F50057'
  },
  'example': {
    emoji: '📋',
    title: 'Пример',
    rgb: '124, 77, 255',
    hex: '#7C4DFF'
  },
  'quote': {
    emoji: '💬',
    title: 'Цитата',
    rgb: '158, 158, 158',
    hex: '#9E9E9E'
  }
};

// Алиасы для совместимости с Obsidian
CALLOUT_STYLES['summary'] = CALLOUT_STYLES['abstract'];
CALLOUT_STYLES['tldr'] = CALLOUT_STYLES['abstract'];
CALLOUT_STYLES['hint'] = CALLOUT_STYLES['tip'];
CALLOUT_STYLES['important'] = CALLOUT_STYLES['danger']; // important -> danger
CALLOUT_STYLES['check'] = CALLOUT_STYLES['success'];
CALLOUT_STYLES['done'] = CALLOUT_STYLES['success'];
CALLOUT_STYLES['fail'] = CALLOUT_STYLES['failure'];
CALLOUT_STYLES['missing'] = CALLOUT_STYLES['failure'];
CALLOUT_STYLES['caution'] = CALLOUT_STYLES['warning'];
CALLOUT_STYLES['attention'] = CALLOUT_STYLES['warning'];
CALLOUT_STYLES['help'] = CALLOUT_STYLES['question'];
CALLOUT_STYLES['faq'] = CALLOUT_STYLES['question'];
CALLOUT_STYLES['cite'] = CALLOUT_STYLES['quote'];
CALLOUT_STYLES['error'] = CALLOUT_STYLES['danger'];

// Настройки Border Style
const CALLOUT_CONFIG = {
  borderWidth: '4px',
  borderRadius: '2px',
  titleOpacity: 0.4,    // 40% для фона заголовка
  contentOpacity: 0.1,  // 10% для фона содержимого
  titlePadding: '6px 12px',
  contentPadding: '12px'
};

// ========================================
// HEADER COLORS (Topaz-Nord)
// ========================================

const HEADER_COLORS = {
  h1: '#BF616A',  // nord11 - красно-розовый
  h2: '#D08770',  // nord12 - коралловый/оранжевый
  h3: '#EBCB8B',  // nord13 - золотисто-желтый
  h4: '#A3BE8C',  // nord14 - зеленый/мятный
  h5: '#88C0D0',  // nord8 - голубой/циан
  h6: '#B48EAD'   // nord15 - лавандовый
};

const HEADER_SIZES = {
  h1: '24pt',
  h2: '20pt',
  h3: '16pt',
  h4: '14pt',
  h5: '12pt',
  h6: '11pt'
};

// ========================================
// TAG STYLES (Topaz-Nord)
// ========================================

const TAG_STYLE = {
  color: '#8fbcbb',                        // nord7
  backgroundColor: 'rgba(143, 188, 187, 0.18)',
  borderColor: 'rgba(143, 188, 187, 0.3)',
  borderWidth: '1px',
  borderRadius: '12px',
  padding: '2px 8px',
  fontSize: '0.9em',
  display: 'inline-block',
  margin: '0 4px'
};

// ========================================
// HELPER FUNCTIONS
// ========================================

/**
 * Генерирует HTML для каллаута (Border Style)
 * @param {string} type - Тип каллаута
 * @param {string} title - Заголовок (опционально)
 * @param {string} content - Содержимое
 * @returns {string} HTML
 */
function generateCalloutHTML(type, title, content) {
  const style = CALLOUT_STYLES[type.toLowerCase()] || CALLOUT_STYLES['note'];
  const displayTitle = title || style.title;
  
  return `
<div style="
  border-left: ${CALLOUT_CONFIG.borderWidth} solid rgb(${style.rgb});
  border-radius: ${CALLOUT_CONFIG.borderRadius};
  margin: 16px 0;
  overflow: hidden;
">
  <div style="
    background-color: rgba(${style.rgb}, ${CALLOUT_CONFIG.titleOpacity});
    padding: ${CALLOUT_CONFIG.titlePadding};
    font-weight: bold;
    font-size: 14px;
    color: rgb(${style.rgb});
  ">
    ${style.emoji} ${displayTitle}
  </div>
  <div style="
    background-color: rgba(${style.rgb}, ${CALLOUT_CONFIG.contentOpacity});
    padding: ${CALLOUT_CONFIG.contentPadding};
    color: #333;
    line-height: 1.6;
  ">
    ${content}
  </div>
</div>
`;
}

/**
 * Генерирует HTML для заголовка (Topaz-Nord)
 * @param {number} level - Уровень (1-6)
 * @param {string} text - Текст
 * @returns {string} HTML
 */
function generateHeaderHTML(level, text) {
  const color = HEADER_COLORS[`h${level}`] || '#000000';
  const size = HEADER_SIZES[`h${level}`] || '14pt';
  
  return `<h${level} style="color: ${color}; font-size: ${size}; font-weight: bold; margin: 1em 0 0.5em 0;">${text}</h${level}>`;
}

/**
 * Генерирует HTML для тега (Topaz-Nord)
 * @param {string} tag - Название тега
 * @returns {string} HTML
 */
function generateTagHTML(tag) {
  return `<span style="
    color: ${TAG_STYLE.color};
    background-color: ${TAG_STYLE.backgroundColor};
    border: ${TAG_STYLE.borderWidth} solid ${TAG_STYLE.borderColor};
    border-radius: ${TAG_STYLE.borderRadius};
    padding: ${TAG_STYLE.padding};
    font-size: ${TAG_STYLE.fontSize};
    display: ${TAG_STYLE.display};
    margin: ${TAG_STYLE.margin};
  ">#${tag}</span>`;
}

/**
 * Конвертирует каллаут Obsidian в HTML
 * @param {string} markdown - Markdown текст
 * @returns {string} HTML
 */
function convertCalloutToHTML(markdown) {
  // Паттерн для каллаутов: > [!type] Title\n> content
  const calloutRegex = /^>\s*\[!(\w+)\]\s*(.*?)\n((?:^>.*$\n?)*)/gm;
  
  return markdown.replace(calloutRegex, (match, type, title, content) => {
    // Убираем > в начале строк
    const cleanContent = content.replace(/^>\s?/gm, '').trim();
    return generateCalloutHTML(type, title, cleanContent);
  });
}

/**
 * Конвертирует теги в HTML
 * @param {string} text - Текст с тегами
 * @returns {string} HTML
 */
function convertTagsToHTML(text) {
  // Паттерн для тегов (избегаем заголовки)
  const tagRegex = /(?<![#\w])#([а-яА-Яa-zA-Z0-9_-]+)/g;
  
  return text.replace(tagRegex, (match, tag) => {
    return generateTagHTML(tag);
  });
}

/**
 * Полная конвертация Markdown → HTML
 * @param {string} markdown - Исходный markdown
 * @returns {string} HTML с стилями
 */
function convertMarkdownToHTML(markdown) {
  let html = markdown;
  
  // 1. Конвертируем каллауты
  html = convertCalloutToHTML(html);
  
  // 2. Конвертируем заголовки
  for (let i = 6; i >= 1; i--) {
    const headerRegex = new RegExp(`^${'#'.repeat(i)}\\s+(.+)$`, 'gm');
    html = html.replace(headerRegex, (match, text) => {
      return generateHeaderHTML(i, text);
    });
  }
  
  // 3. Конвертируем теги
  html = convertTagsToHTML(html);
  
  // 4. Базовое форматирование
  // Жирный текст
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');
  
  // Курсив
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/_(.+?)_/g, '<em>$1</em>');
  
  // Параграфы
  html = html.replace(/\n\n/g, '</p><p>');
  html = '<p>' + html + '</p>';
  
  return html;
}

// ========================================
// EXPORT
// ========================================

module.exports = {
  CALLOUT_STYLES,
  CALLOUT_CONFIG,
  HEADER_COLORS,
  HEADER_SIZES,
  TAG_STYLE,
  generateCalloutHTML,
  generateHeaderHTML,
  generateTagHTML,
  convertCalloutToHTML,
  convertTagsToHTML,
  convertMarkdownToHTML
};

// ========================================
// ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ
// ========================================

/*
// Пример 1: Каллаут "Важно"
const callout = generateCalloutHTML('important', 'Ключевая цель', 
  'Интенсив НЕ является программой снижения веса. Это подготовка к будущим изменениям.');
console.log(callout);

// Пример 2: Заголовки Topaz-Nord
const h1 = generateHeaderHTML(1, 'Интенсив по привычкам питания');
const h2 = generateHeaderHTML(2, 'Подготовка к интенсиву');
const h3 = generateHeaderHTML(3, 'Привлечение участников');
console.log(h1, h2, h3);

// Пример 3: Теги
const tags = '#интенсив #методология #herbalife';
const htmlTags = convertTagsToHTML(tags);
console.log(htmlTags);

// Пример 4: Полная конвертация
const markdown = `
# Интенсив по привычкам питания

#интенсив #методология #herbalife

## Подготовка к интенсиву

> [!important] Ключевая цель
> Интенсив НЕ является программой снижения веса.

Это **очень важно** помнить!
`;

const html = convertMarkdownToHTML(markdown);
console.log(html);
*/
