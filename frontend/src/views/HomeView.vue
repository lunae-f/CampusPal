<script setup>
import { ref, computed, onMounted, watch, onBeforeUpdate } from 'vue';
import { VueDraggable } from 'vue-draggable-plus';
import SyllabusRow from '../components/SyllabusRow.vue';
import { fetchSyllabus } from '../services/syllabusApi.js';

const STORAGE_KEY = 'gpa-calculator-data-v5';
const EVALUATION_RANGES = { '秀': { minScore: 90, maxScore: 100 }, '優': { minScore: 80, maxScore: 89 }, '良': { minScore: 70, maxScore: 79 }, '可': { minScore: 60, maxScore: 69 } };
const crclumcd = ref('s24160');
const rows = ref([]);
const fileInput = ref(null);
const rowRefs = ref([]);

// フィルタリング用の状態
const selectedYear = ref('');
const selectedTerm = ref('');
const selectedCategory = ref('');

// フィルタリングの選択肢を動的に生成
const availableYears = computed(() => [...new Set(rows.value.map(row => row.rishunen).filter(Boolean))].sort((a, b) => b - a));
const availableTerms = computed(() => [...new Set(rows.value.map(row => row.syllabusData?.term).filter(Boolean))].sort());
const availableCategories = computed(() => [...new Set(rows.value.map(row => row.syllabusData?.category?.split('・')[0]).filter(Boolean))].sort());

// 行が表示されるべきかどうかを判断する関数
const shouldShowRow = (row) => {
  const yearMatch = !selectedYear.value || row.rishunen === selectedYear.value;
  const termMatch = !selectedTerm.value || row.syllabusData?.term === selectedTerm.value;
  const categoryMatch = !selectedCategory.value || row.syllabusData?.category?.startsWith(selectedCategory.value);
  return yearMatch && termMatch && categoryMatch;
};

onBeforeUpdate(() => {
  rowRefs.value = [];
});

const onDragStart = (index) => {
  draggedIndex.value = index;
};
const onDrop = (targetIndex) => {
  if (draggedIndex.value === null || draggedIndex.value === targetIndex) {
    draggedIndex.value = null;
    return;
  }
  const draggedItem = rows.value.splice(draggedIndex.value, 1)[0];
  rows.value.splice(targetIndex, 0, draggedItem);
  draggedIndex.value = null;
};

const saveToFile = () => { try { const simplifiedRows = rows.value.filter(row => row.kougicd).map(row => ({ rishunen: row.rishunen, kougicd: row.kougicd, evaluation: row.evaluation || '' })); const dataToSave = { crclumcd: crclumcd.value, rows: simplifiedRows }; const jsonString = JSON.stringify(dataToSave, null, 2); const blob = new Blob([jsonString], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'CampusPal_data.json'; document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url); } catch (error) { alert('ファイルの保存に失敗しました。'); console.error(error); } };
const triggerFileInput = () => { fileInput.value.click(); };
const handleFileLoad = (event) => { const file = event.target.files[0]; if (!file) return; const reader = new FileReader(); reader.onload = (e) => { try { const content = e.target.result; let loadedData = {}; if (file.name.endsWith('.csv')) { const lines = content.trim().split('\n'); const simplifiedRows = []; for (let i = 1; i < lines.length; i++) { const parts = lines[i].split(','); if (parts.length >= 3) { simplifiedRows.push({ rishunen: parts[0].trim(), kougicd: parts[1].trim(), evaluation: parts[2].trim() }); } } loadedData = { rows: simplifiedRows, crclumcd: crclumcd.value }; } else { loadedData = JSON.parse(content); } if (loadedData && Array.isArray(loadedData.rows)) { crclumcd.value = loadedData.crclumcd || crclumcd.value; const newRows = loadedData.rows.map((simpleRow, index) => ({ id: index, rishunen: simpleRow.rishunen, kougicd: simpleRow.kougicd, evaluation: simpleRow.evaluation, syllabusData: null, isLoading: false, error: null })); rows.value = newRows; fetchSyllabusDataForRows(rows.value); alert('データを読み込みました。'); } else { throw new Error('ファイルの形式が正しくありません。'); } } catch (error) { alert(`ファイルの読み込みに失敗しました: ${error.message}`); console.error(error); } }; reader.readAsText(file); event.target.value = ''; };
const rowMetadata = computed(() => { const metadata = {}; const kougicdCounts = {}; const coursesByName = {}; rows.value.forEach(row => { metadata[row.id] = { isDuplicate: false, isOlderAttempt: false }; if (row.kougicd) { kougicdCounts[row.kougicd] = (kougicdCounts[row.kougicd] || 0) + 1; } if (row.syllabusData?.course_name) { const name = row.syllabusData.course_name; if (!coursesByName[name]) coursesByName[name] = []; coursesByName[name].push(row); } }); rows.value.forEach(row => { if (row.kougicd && kougicdCounts[row.kougicd] > 1) { metadata[row.id].isDuplicate = true; } }); const getTermRank = (term) => { const order = { '前期前半': 1, '前期後半': 2, '前期': 3, '後期前半': 4, '後期後半': 5, '後期': 6 }; return order[term] || 0; }; for (const courseName in coursesByName) { const group = coursesByName[courseName]; if (group.length > 1) { group.sort((a, b) => { if (a.rishunen !== b.rishunen) return b.rishunen - a.rishunen; const rankA = getTermRank(a.syllabusData.term); const rankB = getTermRank(b.syllabusData.term); return rankB - rankA; }); for (let i = 1; i < group.length; i++) { metadata[group[i].id].isOlderAttempt = true; } } } return metadata; });
const finalRowsForCalc = computed(() => { return rows.value.filter(row => row.kougicd && row.syllabusData?.course_name && !rowMetadata.value[row.id]?.isOlderAttempt);});
const gpaStats = computed(() => { let totalMinGpProduct = 0, totalMaxGpProduct = 0, totalAttemptedCredits = 0, totalEarnedCredits = 0, totalInProgressCredits = 0; for (const row of finalRowsForCalc.value) { const credits = Number(row.syllabusData?.credits); if (!credits) continue; if (row.evaluation) { totalAttemptedCredits += credits; let minGp = 0, maxGp = 0; if (row.evaluation !== '不可') { const range = EVALUATION_RANGES[row.evaluation]; if (range) { minGp = (range.minScore - 50) / 10; maxGp = (range.maxScore - 50) / 10; } totalEarnedCredits += credits; } totalMinGpProduct += minGp * credits; totalMaxGpProduct += maxGp * credits; } else { totalInProgressCredits += credits; } } const minGpa = totalAttemptedCredits > 0 ? (totalMinGpProduct / totalAttemptedCredits) : 0; const maxGpa = totalAttemptedCredits > 0 ? (totalMaxGpProduct / totalAttemptedCredits) : 0; const avgGpa = (minGpa + maxGpa) / 2; const currentRate = totalAttemptedCredits > 0 ? (totalEarnedCredits / totalAttemptedCredits * 100) : 0; const prospectiveTotalAttempted = totalAttemptedCredits + totalInProgressCredits; const prospectiveTotalEarned = totalEarnedCredits + totalInProgressCredits; const prospectiveRate = prospectiveTotalAttempted > 0 ? (prospectiveTotalEarned / prospectiveTotalAttempted * 100) : 0; return { totalAttemptedCredits, totalEarnedCredits, totalInProgressCredits, currentRate: currentRate.toFixed(1), prospectiveRate: prospectiveRate.toFixed(1), minGpa: minGpa.toFixed(3), maxGpa: maxGpa.toFixed(3), avgGpa: avgGpa.toFixed(3) }; });
const creditsByCategory = computed(() => { const categoryTotals = {}; for (const row of finalRowsForCalc.value) { if (row.evaluation && row.evaluation !== '不可' && row.syllabusData?.category && row.syllabusData?.credits) { const fullCategory = row.syllabusData.category; const categoryKey = fullCategory.split('・')[0]; const credits = Number(row.syllabusData.credits); categoryTotals[categoryKey] = (categoryTotals[categoryKey] || 0) + credits; } } return categoryTotals; });
const groupedAndSortedCreditsByTerm = computed(() => { const termTotals = {}; for (const row of finalRowsForCalc.value) { if (row.rishunen && row.syllabusData?.term && row.syllabusData?.credits) { const termKey = `${row.rishunen}年度 ${row.syllabusData.term}`; if (!termTotals[termKey]) { termTotals[termKey] = { earned: 0, attempted: 0, inProgress: 0 }; } const credits = Number(row.syllabusData.credits); if(row.evaluation) { termTotals[termKey].attempted += credits; if (row.evaluation !== '不可') { termTotals[termKey].earned += credits; } } else { termTotals[termKey].inProgress += credits; } } } const grouped = {}; const termOrder = [ '通年', '前期', '前期前半', '前期後半', '後期', '後期後半', '通年（卒研）', '集中（前期）', '集中（後期）', '集中（通年）', '通年（事例）', '通年（大学院）' ]; const getOrderIndex = (termName) => { const index = termOrder.indexOf(termName); return index === -1 ? Infinity : index; }; for (const fullTermKey in termTotals) { const parts = fullTermKey.split('年度 '); const year = parts[0]; const termName = parts[1]; if (!grouped[year]) { grouped[year] = { terms: [], yearStats: { earned: 0, attempted: 0, inProgress: 0 } }; } const termStat = termTotals[fullTermKey]; grouped[year].terms.push({ termName: termName, stats: termStat }); grouped[year].yearStats.earned += termStat.earned; grouped[year].yearStats.attempted += termStat.attempted; grouped[year].yearStats.inProgress += termStat.inProgress; } for (const year in grouped) { grouped[year].terms.sort((a, b) => getOrderIndex(a.termName) - getOrderIndex(b.termName)); } return Object.keys(grouped).sort((a, b) => a - b).map(year => ({ year: year, ...grouped[year] })); });
const handleFetch = async (row) => { row.isLoading = true; row.error = null; try { const data = await fetchSyllabus({ kougicd: row.kougicd, rishunen: row.rishunen, crclumcd: crclumcd.value }); row.syllabusData = data; } catch (e) { row.error = e.message; row.syllabusData = null; } finally { row.isLoading = false; } };
const fetchSyllabusDataForRows = async (rowsToFetch) => { for (const row of rowsToFetch) { if (row.kougicd && row.rishunen) { await handleFetch(row); } } };
const addNewRow = () => { const lastRow = rows.value.length > 0 ? rows.value[rows.value.length - 1] : null; const newYear = lastRow ? lastRow.rishunen : '2024'; rows.value.push({ id: rows.value.length, rishunen: newYear, kougicd: '', evaluation: '', syllabusData: null, isLoading: false, error: null }); };
const clearRowData = (rowToClear) => { rowToClear.evaluation = ''; rowToClear.syllabusData = null; rowToClear.isLoading = false; rowToClear.error = null; };
onMounted(() => { const savedDataString = localStorage.getItem(STORAGE_KEY); if (savedDataString) { try { const savedData = JSON.parse(savedDataString); if (savedData.rows.length > 0) { crclumcd.value = savedData.crclumcd; const newRows = savedData.rows.map((simpleRow, index) => ({ id: index, rishunen: simpleRow.rishunen, kougicd: simpleRow.kougicd, evaluation: simpleRow.evaluation, syllabusData: null, isLoading: false, error: null })); rows.value = newRows; fetchSyllabusDataForRows(rows.value); return; } } catch (e) { console.error("Failed to parse localStorage data:", e); localStorage.removeItem(STORAGE_KEY); } } rows.value = Array.from({ length: 15 }, (_, i) => ({ id: i, rishunen: '2024', kougicd: '', evaluation: '', syllabusData: null, isLoading: false, error: null })); });
watch(rows, (newRows) => { const simplifiedRows = newRows.filter(row => row.kougicd).map(row => ({ rishunen: row.rishunen, kougicd: row.kougicd, evaluation: row.evaluation || '' })); const dataToSave = { crclumcd: crclumcd.value, rows: simplifiedRows }; localStorage.setItem(STORAGE_KEY, JSON.stringify(dataToSave)); if (newRows.length > 0) { const lastRow = newRows[newRows.length - 1]; if (lastRow.kougicd || lastRow.evaluation) { addNewRow(); } } }, { deep: true });
</script>

<template>
  <main class="container">
    <header class="header">
      <h1>CampusPal</h1>
      <div class="header-controls">
        <div class="file-operations">
          <button @click="saveToFile" class="io-button">ファイルに保存</button>
          <button @click="triggerFileInput" class="io-button">ファイルから読込</button>
          <input type="file" ref="fileInput" @change="handleFileLoad" accept=".json,.csv" style="display: none;" />
        </div>
        <div class="global-input" title="s+学籍番号上5桁">
          <label for="crclumcd" class="tooltip-label">カリキュラムコード:</label>
          <input id="crclumcd" v-model="crclumcd" />
        </div>
      </div>
    </header>
    <section class="gpa-display">
      <div class="gpa-item">
        <div class="gpa-label">f-GPA</div>
        <div class="gpa-main-value">{{ gpaStats.avgGpa }}</div>
        <div class="gpa-range">({{ gpaStats.minGpa }} ~ {{ gpaStats.maxGpa }})</div>
      </div>
      <div class="gpa-item">
        <div class="gpa-label">単位数</div>
        <div class="gpa-main-value">
          {{ gpaStats.totalEarnedCredits }} / {{ gpaStats.totalAttemptedCredits }}
          <span class="in-progress-credits" v-if="gpaStats.totalInProgressCredits > 0">(+{{ gpaStats.totalInProgressCredits }})</span>
        </div>
        <div class="gpa-range">
          取得率: {{ gpaStats.currentRate }}%
          <span v-if="gpaStats.totalInProgressCredits > 0">(見込: {{ gpaStats.prospectiveRate }}%)</span>
        </div>
      </div>
    </section>
    <div class="stats-container">
      <section class="category-credits-display">
        <h3>取得単位数（分野系列別）</h3>
        <div class="category-grid">
          <div v-for="(credits, category) in creditsByCategory" :key="category" class="category-item">
            <span class="category-name">{{ category }}</span>
            <span class="category-value">{{ credits }}単位</span>
          </div>
        </div>
      </section>
      <section class="term-credits-display">
        <h3>単位数（開講時期別）</h3>
        <div class="term-grid">
          <div v-for="group in groupedAndSortedCreditsByTerm" :key="group.year" class="year-group">
            <div class="year-header">
              <h4>{{ group.year }}年度</h4>
              <span class="year-total">{{ group.yearStats.earned }} / {{ group.yearStats.attempted }} <span class="in-progress-credits" v-if="group.yearStats.inProgress > 0">(+{{ group.yearStats.inProgress }})</span> 単位</span>
            </div>
            <div v-for="item in group.terms" :key="item.termName" class="term-item">
              <span class="term-name">{{ item.termName }}</span>
              <span class="term-value">{{ item.stats.earned }} / {{ item.stats.attempted }} <span class="in-progress-credits" v-if="item.stats.inProgress > 0">(+{{ item.stats.inProgress }})</span> 単位</span>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- フィルタリングUIを追加 -->
    <section class="filter-controls">
      <div class="filter-group">
        <label for="filter-year">年度</label>
        <select id="filter-year" v-model="selectedYear">
          <option value="">すべて</option>
          <option v-for="year in availableYears" :key="year" :value="year">{{ year }}</option>
        </select>
      </div>
      <div class="filter-group">
        <label for="filter-term">開講時期</label>
        <select id="filter-term" v-model="selectedTerm">
          <option value="">すべて</option>
          <option v-for="term in availableTerms" :key="term" :value="term">{{ term }}</option>
        </select>
      </div>
      <div class="filter-group">
        <label for="filter-category">分野系列</label>
        <select id="filter-category" v-model="selectedCategory">
          <option value="">すべて</option>
          <option v-for="cat in availableCategories" :key="cat" :value="cat">{{ cat }}</option>
        </select>
      </div>
    </section>

    <div class="table-header">
      <div class="col-handle"></div>
      <div class="col-index">#</div>
      <div class="col-year">年度</div>
      <div class="col-code">講義コード</div>
      <div class="col-term">学期</div>
      <div class="col-category">分野系列</div>
      <div class="col-info">講義名</div>
      <div class="col-instructors">担当者</div>
      <div class="col-credits">単位数</div>
      <div class="col-eval">評価</div>
    </div>
    <VueDraggable
      v-model="rows"
      tag="div"
      class="syllabus-table"
      handle=".drag-handle"
      animation="150"
      ghostClass="draggable-ghost"
    >
      <div v-for="(row, index) in rows" :key="row.id" class="drag-wrapper" v-show="shouldShowRow(row)">
        <SyllabusRow
          :row-index="index"
          v-model:rishunen="row.rishunen"
          v-model:kougicd="row.kougicd"
          v-model:evaluation="row.evaluation"
          :syllabus-data="row.syllabusData"
          :is-loading="row.isLoading"
          :error="row.error"
          :is-duplicate="rowMetadata[row.id]?.isDuplicate"
          :is-older-attempt="rowMetadata[row.id]?.isOlderAttempt"
          :crclumcd="crclumcd"
          @fetch-request="handleFetch(row)"
          @clear-row="clearRowData(row)"
          @drag-start="onDragStart(index)"
        />
      </div>
    </VueDraggable>
  </main>
</template>

<style scoped>
/* PC用のスタイル */
.container { padding: 20px; font-family: sans-serif; max-width: 1600px; margin: 0 auto; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 10px;}
.header-controls { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
.file-operations { display: flex; gap: 8px; }
.io-button { padding: 6px 12px; border: 1px solid #6c757d; background-color: #fff; color: #6c757d; border-radius: 4px; cursor: pointer; font-size: 0.9em; }
.io-button:hover { background-color: #f8f9fa; }
.global-input { display: flex; align-items: center; gap: 8px; }
.global-input input {
  padding: 6px;
  border: 1px solid #ccc;
  border-radius: 4px;
  width: 120px;
}
.tooltip-label { cursor: help; border-bottom: 1px dotted #6c757d; }
.gpa-display { background-color: #e9f7ef; border: 1px solid #a9d6b8; border-radius: 8px; padding: 16px; margin-bottom: 10px; display: flex; justify-content: space-around; flex-wrap: wrap; gap: 15px;}
.gpa-item { text-align: center; }
.gpa-label { font-size: 0.9em; color: #333; }
.gpa-main-value { font-weight: bold; font-size: 2em; color: #00754a; line-height: 1.2; }
.gpa-range { font-size: 0.8em; color: #6c757d; }
.in-progress-credits { font-size: 0.8em; color: #00754a; }
.stats-container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
.category-credits-display, .term-credits-display { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 16px; }
.category-credits-display h3, .term-credits-display h3 { margin-top: 0; margin-bottom: 12px; font-size: 1.1em; border-bottom: 1px solid #ccc; padding-bottom: 8px; }
.category-grid { display: grid; grid-template-columns: 1fr; gap: 8px; font-size: 0.9em; }
.category-item { display: flex; justify-content: space-between; }
.category-value { font-weight: bold; }
.term-grid { display: flex; flex-direction: column; gap: 16px; }
.year-group {}
.year-header { display: flex; justify-content: space-between; align-items: baseline; font-size: 1em; font-weight: bold; margin: 0 0 8px 0; padding-bottom: 4px; border-bottom: 1px solid #e0e0e0; }
.year-header h4 { margin: 0; }
.year-total { font-size: 0.9em; font-weight: normal; color: #555; }
.term-item { display: flex; justify-content: space-between; padding-left: 10px; padding-bottom: 4px; font-size: 0.9em; }
.term-value { font-weight: bold; }
.filter-controls {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
}
.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
.filter-group label {
  font-size: 0.9em;
  font-weight: bold;
  white-space: nowrap; /* 文字列の改行を防ぐ */
}
.filter-group select {
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #ccc;
}
.table-header { display: grid; grid-template-columns: 30px 30px 60px 100px 100px 160px 1fr 120px 50px 80px; gap: 12px; font-weight: bold; border-bottom: 2px solid #333; padding: 0 4px 8px 4px; color: #555; font-size: 0.8em; }
.table-header > div { text-align: center; }
.table-header .col-info, .table-header .col-category, .table-header .col-instructors { text-align: left; }
.drag-wrapper { border-bottom: 1px solid #eee; }
.draggable-ghost { opacity: 0.5; background: #cce5ff; }

/* --- Mobile View --- */
@media (max-width: 768px) {
  .container { padding: 10px; }
  .header { flex-direction: column; align-items: stretch; }
  .header-controls { flex-direction: column; align-items: stretch; gap: 10px; }
  .stats-container { grid-template-columns: 1fr; }
  .table-header { display: none; }
  .syllabus-table { display: flex; flex-direction: column; gap: 10px; }
  .drag-wrapper {
    border: 1px solid #ddd;
    border-radius: 8px;
    background-color: #fff;
  }

  /* --- Final Card Layout (Revision 17) --- */
  :deep(.syllabus-row) {
    display: grid;
    grid-template-columns: auto auto repeat(10, 1fr);
    gap: 8px 10px;
    padding: 12px;
    align-items: center;
  }
  :deep(.syllabus-row > div) {
    padding: 0; border: none; text-align: left;
  }
  :deep(.syllabus-row > div::before) {
    content: attr(data-label);
    font-size: 0.8em;
    color: #666;
    margin-bottom: 4px;
    display: block;
  }

  /* grid-area definitions */
  :deep(.col-handle) { grid-area: 1 / 1; }
  :deep(.col-index) { grid-area: 1 / 2; font-weight: bold; }
  :deep(.col-year) { grid-area: 1 / 3 / 1 / 6; }
  :deep(.col-code) { grid-area: 1 / 6 / 1 / 10; }
  :deep(.col-term) { grid-area: 1 / 10 / 1 / 13; }
  :deep(.col-info) { grid-area: 2 / 1 / 2 / 13; }
  :deep(.col-category) { grid-area: 3 / 1 / 3 / 8; }
  :deep(.col-instructors) { grid-area: 3 / 8 / 3 / 13; }
  :deep(.col-eval) { grid-area: 4 / 1 / 4 / 8; }
  :deep(.col-credits) { grid-area: 4 / 8 / 4 / 13; text-align: right; }
  :deep(.col-gpa) { grid-area: 5 / 1 / 5 / 8; }

  /* --- Style adjustments --- */
  /* 分野系列と担当者のスタイル */
  :deep(.col-category),
  :deep(.col-instructors) {
    font-size: 0.9em;
    color: #555;
  }
  :deep(.col-category select),
  :deep(.col-instructors input) {
    color: #555;
    font-size: 1em;
  }

  /* 1行目のラベルを非表示に */
  :deep(.col-handle)::before, :deep(.col-index)::before, :deep(.col-year)::before,
  :deep(.col-code)::before, :deep(.col-term)::before {
    display: none;
  }
  
  /* 右寄せ要素のラベルは左揃えに戻す */
  :deep(.col-credits)::before, :deep(.col-gpa)::before {
    text-align: left;
  }
  
  /* 単位数セクションの調整 */
  :deep(.col-credits .credits-input) {
    display: inline-block;
    width: 4em;
    vertical-align: middle;
  }
  :deep(.col-credits)::after {
    content: "単位";
    display: inline-block;
    vertical-align: middle;
    margin-left: 4px;
  }
  
  /* 汎用入力スタイル */
  :deep(input), :deep(select) {
    font-size: 1em; padding: 6px; background-color: #f7f7f7;
    border: 1px solid #ccc; border-radius: 4px;
    width: 100%; box-sizing: border-box;
  }
}
</style>