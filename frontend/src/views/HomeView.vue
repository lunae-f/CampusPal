<script setup>
import { ref, computed, onMounted, watch, onBeforeUpdate } from 'vue';
import SyllabusRow from '../components/SyllabusRow.vue';
import { fetchSyllabus } from '../services/syllabusApi.js';

const STORAGE_KEY = 'gpa-calculator-data-v5';
const EVALUATION_RANGES = { '秀': { minScore: 90, maxScore: 100 }, '優': { minScore: 80, maxScore: 89 }, '良': { minScore: 70, maxScore: 79 }, '可': { minScore: 60, maxScore: 69 } };
const crclumcd = ref('s24160');
const rows = ref([]);
const fileInput = ref(null);
const rowRefs = ref([]);

onBeforeUpdate(() => {
  rowRefs.value = [];
});

const handleFocusNext = (currentIndex) => {
  const nextRowComponent = rowRefs.value[currentIndex + 1];
  if (nextRowComponent) {
    nextRowComponent.focusInput();
  }
};

const saveToFile = () => {
  try {
    const simplifiedRows = rows.value.filter(row => row.kougicd).map(row => ({ rishunen: row.rishunen, kougicd: row.kougicd, evaluation: row.evaluation || '' }));
    const dataToSave = { crclumcd: crclumcd.value, rows: simplifiedRows };
    const jsonString = JSON.stringify(dataToSave, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'CampusPal_data.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (error) {
    alert('ファイルの保存に失敗しました。');
    console.error(error);
  }
};

const triggerFileInput = () => {
  fileInput.value.click();
};

const handleFileLoad = (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const content = e.target.result;
      let loadedData = {};
      if (file.name.endsWith('.csv')) {
        const lines = content.trim().split('\n');
        const simplifiedRows = [];
        for (let i = 1; i < lines.length; i++) {
          const parts = lines[i].split(',');
          if (parts.length >= 3) {
            simplifiedRows.push({ rishunen: parts[0].trim(), kougicd: parts[1].trim(), evaluation: parts[2].trim() });
          }
        }
        loadedData = { rows: simplifiedRows, crclumcd: crclumcd.value };
      } else {
        loadedData = JSON.parse(content);
      }
      if (loadedData && Array.isArray(loadedData.rows)) {
        crclumcd.value = loadedData.crclumcd || crclumcd.value;
        const newRows = loadedData.rows.map((simpleRow, index) => ({ id: index, rishunen: simpleRow.rishunen, kougicd: simpleRow.kougicd, evaluation: simpleRow.evaluation, syllabusData: null, isLoading: false, error: null }));
        rows.value = newRows;
        fetchSyllabusDataForRows(rows.value);
        alert('データを読み込みました。');
      } else {
        throw new Error('ファイルの形式が正しくありません。');
      }
    } catch (error) {
      alert(`ファイルの読み込みに失敗しました: ${error.message}`);
      console.error(error);
    }
  };
  reader.readAsText(file);
  event.target.value = '';
};

const rowMetadata = computed(() => { const metadata = {}; const kougicdCounts = {}; const coursesByName = {}; rows.value.forEach(row => { metadata[row.id] = { isDuplicate: false, isOlderAttempt: false }; if (row.kougicd) { kougicdCounts[row.kougicd] = (kougicdCounts[row.kougicd] || 0) + 1; } if (row.syllabusData?.course_name) { const name = row.syllabusData.course_name; if (!coursesByName[name]) coursesByName[name] = []; coursesByName[name].push(row); } }); rows.value.forEach(row => { if (row.kougicd && kougicdCounts[row.kougicd] > 1) { metadata[row.id].isDuplicate = true; } }); const getTermRank = (term) => { const order = { '前期前半': 1, '前期後半': 2, '前期': 3, '後期前半': 4, '後期後半': 5, '後期': 6 }; return order[term] || 0; }; for (const courseName in coursesByName) { const group = coursesByName[courseName]; if (group.length > 1) { group.sort((a, b) => { if (a.rishunen !== b.rishunen) return b.rishunen - a.rishunen; const rankA = getTermRank(a.syllabusData.term); const rankB = getTermRank(b.syllabusData.term); return rankB - rankA; }); for (let i = 1; i < group.length; i++) { metadata[group[i].id].isOlderAttempt = true; } } } return metadata; });
const finalRowsForCalc = computed(() => { return rows.value.filter(row => row.evaluation && row.syllabusData?.course_name && !rowMetadata.value[row.id]?.isOlderAttempt);});
const gpaStats = computed(() => { let totalMinGpProduct = 0, totalMaxGpProduct = 0, totalAttemptedCredits = 0, totalEarnedCredits = 0; for (const row of finalRowsForCalc.value) { const credits = Number(row.syllabusData?.credits); if (!credits) continue; let minGp = 0, maxGp = 0; if (row.evaluation !== '不可') { const range = EVALUATION_RANGES[row.evaluation]; if (range) { minGp = (range.minScore - 50) / 10; maxGp = (range.maxScore - 50) / 10; } totalEarnedCredits += credits; } totalMinGpProduct += minGp * credits; totalMaxGpProduct += maxGp * credits; totalAttemptedCredits += credits; } const minGpa = totalAttemptedCredits > 0 ? (totalMinGpProduct / totalAttemptedCredits) : 0; const maxGpa = totalAttemptedCredits > 0 ? (totalMaxGpProduct / totalAttemptedCredits) : 0; const avgGpa = (minGpa + maxGpa) / 2; const acquisitionRate = totalAttemptedCredits > 0 ? (totalEarnedCredits / totalAttemptedCredits * 100) : 0; return { totalAttemptedCredits, totalEarnedCredits, acquisitionRate: acquisitionRate.toFixed(1), minGpa: minGpa.toFixed(3), maxGpa: maxGpa.toFixed(3), avgGpa: avgGpa.toFixed(3) }; });
const creditsByCategory = computed(() => { const categoryTotals = {}; for (const row of finalRowsForCalc.value) { if (row.evaluation !== '不可' && row.syllabusData?.category && row.syllabusData?.credits) { const fullCategory = row.syllabusData.category; const categoryKey = fullCategory.split('・')[0]; const credits = Number(row.syllabusData.credits); categoryTotals[categoryKey] = (categoryTotals[categoryKey] || 0) + credits; } } return categoryTotals; });
const handleFetch = async (row) => { row.isLoading = true; row.error = null; try { const data = await fetchSyllabus({ kougicd: row.kougicd, rishunen: row.rishunen, crclumcd: crclumcd.value }); row.syllabusData = data; } catch (e) { row.error = e.message; row.syllabusData = null; } finally { row.isLoading = false; } };
const fetchSyllabusDataForRows = async (rowsToFetch) => { for (const row of rowsToFetch) { if (row.kougicd && row.rishunen) { await handleFetch(row); await new Promise(resolve => setTimeout(resolve, 200)); } } };
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
        <div class="gpa-label">取得 / 履修 単位数</div>
        <div class="gpa-main-value">{{ gpaStats.totalEarnedCredits }} / {{ gpaStats.totalAttemptedCredits }}</div>
        <div class="gpa-range">取得率: {{ gpaStats.acquisitionRate }}%</div>
      </div>
    </section>
    <section class="category-credits-display">
      <h3>取得単位数（分野系列別）</h3>
      <div class="category-grid">
        <div v-for="(credits, category) in creditsByCategory" :key="category" class="category-item">
          <span class="category-name">{{ category }}</span>
          <span class="category-value">{{ credits }}単位</span>
        </div>
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
    <div class="syllabus-table">
      <div 
        v-for="(row, index) in rows"
        :key="row.id"
        @drop.prevent="onDrop(index)"
        @dragover.prevent
        class="drag-wrapper"
        :class="{ 'dragging': draggedIndex === index }"
      >
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
    </div>
  </main>
</template>

<style scoped>
.container { padding: 20px; font-family: sans-serif; max-width: 1600px; margin: 0 auto; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.header-controls { display: flex; align-items: center; gap: 24px; }
.file-operations { display: flex; gap: 8px; }
.io-button { padding: 6px 12px; border: 1px solid #6c757d; background-color: #fff; color: #6c757d; border-radius: 4px; cursor: pointer; font-size: 0.9em; }
.io-button:hover { background-color: #f8f9fa; }
.global-input { display: flex; align-items: center; gap: 8px; }
.global-input input { padding: 6px; border: 1px solid #ccc; border-radius: 4px; }
.tooltip-label {
  cursor: help;
  border-bottom: 1px dotted #6c757d;
}
.gpa-display { background-color: #e9f7ef; border: 1px solid #a9d6b8; border-radius: 8px; padding: 16px; margin-bottom: 10px; display: flex; justify-content: space-around; }
.gpa-item { text-align: center; }
.gpa-label { font-size: 0.9em; color: #333; }
.gpa-main-value { font-weight: bold; font-size: 2em; color: #00754a; line-height: 1.2; }
.gpa-range { font-size: 0.8em; color: #6c757d; }
.category-credits-display { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 16px; margin-bottom: 20px; }
.category-credits-display h3 { margin-top: 0; margin-bottom: 12px; font-size: 1.1em; border-bottom: 1px solid #ccc; padding-bottom: 8px; }
.category-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 8px 32px; font-size: 0.9em; }
.category-item { display: flex; justify-content: flex-start; align-items: baseline; gap: 0.8em; }
.category-value { font-weight: bold; }
.table-header {
  display: grid;
  grid-template-columns: 30px 30px 60px 100px 100px 160px 1fr 120px 50px 80px;
  gap: 12px;
  font-weight: bold;
  border-bottom: 2px solid #333;
  padding: 0 4px 8px 4px;
  color: #555;
  font-size: 0.8em;
}
.table-header > div {
  text-align: center;
}
.table-header .col-info,
.table-header .col-category,
.table-header .col-instructors {
  text-align: left;
}
.drag-wrapper {
  border-bottom: 1px solid #eee;
}
.dragging {
  opacity: 0.5;
  background: #cce5ff;
}
</style>
