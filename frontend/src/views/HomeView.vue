<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import SyllabusRow from '../components/SyllabusRow.vue';
import { fetchSyllabus } from '../services/syllabusApi.js';

const STORAGE_KEY = 'gpa-calculator-data-v4';
const EVALUATION_RANGES = { '秀': { minScore: 90, maxScore: 100 }, '優': { minScore: 80, maxScore: 89 }, '良': { minScore: 70, maxScore: 79 }, '可': { minScore: 60, maxScore: 69 } };
const crclumcd = ref('s24160');
const rows = ref([]);

const rowMetadata = computed(() => {
  const metadata = {}; const kougicdCounts = {}; const coursesByName = {};
  rows.value.forEach(row => {
    metadata[row.id] = { isDuplicate: false, isOlderAttempt: false };
    if (row.kougicd) { kougicdCounts[row.kougicd] = (kougicdCounts[row.kougicd] || 0) + 1; }
    if (row.syllabusData?.course_name) { const name = row.syllabusData.course_name; if (!coursesByName[name]) coursesByName[name] = []; coursesByName[name].push(row); }
  });
  rows.value.forEach(row => { if (row.kougicd && kougicdCounts[row.kougicd] > 1) { metadata[row.id].isDuplicate = true; } });
  const getTermRank = (term) => { const order = { '前期前半': 1, '前期後半': 2, '前期': 3, '後期前半': 4, '後期後半': 5, '後期': 6 }; return order[term] || 0; };
  for (const courseName in coursesByName) {
    const group = coursesByName[courseName];
    if (group.length > 1) {
      group.sort((a, b) => { if (a.rishunen !== b.rishunen) return b.rishunen - a.rishunen; const rankA = getTermRank(a.syllabusData.term); const rankB = getTermRank(b.syllabusData.term); return rankB - rankA; });
      for (let i = 1; i < group.length; i++) { metadata[group[i].id].isOlderAttempt = true; }
    }
  }
  return metadata;
});

const finalRowsForCalc = computed(() => {
  return rows.value.filter(row => row.evaluation && row.syllabusData?.course_name && !rowMetadata.value[row.id]?.isOlderAttempt);
});

const gpaStats = computed(() => {
  let totalMinGpProduct = 0, totalMaxGpProduct = 0, totalCredits = 0;
  for (const row of finalRowsForCalc.value) {
    const credits = Number(row.syllabusData?.credits);
    if (!credits) continue;
    let minGp = 0, maxGp = 0;
    if (row.evaluation !== '不可') {
      const range = EVALUATION_RANGES[row.evaluation];
      if (range) { minGp = (range.minScore - 50) / 10; maxGp = (range.maxScore - 50) / 10; }
    }
    totalMinGpProduct += minGp * credits;
    totalMaxGpProduct += maxGp * credits;
    totalCredits += credits;
  }
  const minGpa = totalCredits > 0 ? (totalMinGpProduct / totalCredits).toFixed(3) : '0.000';
  const maxGpa = totalCredits > 0 ? (totalMaxGpProduct / totalCredits).toFixed(3) : '0.000';
  return { totalCredits, minGpa, maxGpa };
});

// 分野系列ごとの取得単位数計算ロジックを修正
const creditsByCategory = computed(() => {
  const categoryTotals = {};
  for (const row of finalRowsForCalc.value) {
    if (row.evaluation !== '不可' && row.syllabusData?.category && row.syllabusData?.credits) {
      const fullCategory = row.syllabusData.category;
      // 「・」で分割し、最初の部分をキーとして使用
      const categoryKey = fullCategory.split('・')[0];
      const credits = Number(row.syllabusData.credits);
      categoryTotals[categoryKey] = (categoryTotals[categoryKey] || 0) + credits;
    }
  }
  return categoryTotals;
});

const handleFetch = async (row) => {
  row.isLoading = true;
  row.error = null;
  try {
    const data = await fetchSyllabus({ kougicd: row.kougicd, rishunen: row.rishunen, crclumcd: crclumcd.value });
    row.syllabusData = data;
  } catch (e) {
    row.error = e.message;
    row.syllabusData = null;
  } finally {
    row.isLoading = false;
  }
};
const addNewRow = () => { rows.value.push({ id: rows.value.length, rishunen: '2024', kougicd: '', evaluation: '', syllabusData: null, isLoading: false, error: null }); };
const clearRowData = (rowToClear) => {
  rowToClear.evaluation = '';
  rowToClear.syllabusData = null;
  rowToClear.isLoading = false;
  rowToClear.error = null;
};
onMounted(() => {
  const savedData = localStorage.getItem(STORAGE_KEY);
  if (savedData && JSON.parse(savedData).length > 0) {
    rows.value = JSON.parse(savedData);
  } else {
    rows.value = Array.from({ length: 15 }, (_, i) => ({ id: i, rishunen: '2024', kougicd: '', evaluation: '', syllabusData: null, isLoading: false, error: null }));
  }
});
watch(rows, (newRows) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(newRows));
  if (newRows.length > 0) {
    const lastRow = newRows[newRows.length - 1];
    if (lastRow.kougicd || lastRow.evaluation) { addNewRow(); }
  }
}, { deep: true });
</script>

<template>
  <main class="container">
    <header class="header">
      <h1>CampusPal</h1>
      <div class="global-input">
        <label for="crclumcd">カリキュラムコード:</label>
        <input id="crclumcd" v-model="crclumcd" />
      </div>
    </header>
    <section class="gpa-display">
      <div>f-GPA: <span class="gpa-value">{{ gpaStats.minGpa }} ~ {{ gpaStats.maxGpa }}</span></div>
      <div>合計履修単位数: <span>{{ gpaStats.totalCredits }}</span></div>
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
      <SyllabusRow
        v-for="row in rows"
        :key="row.id"
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
      />
    </div>
  </main>
</template>

<style scoped>
.container { padding: 20px; font-family: sans-serif; max-width: 1600px; margin: 0 auto; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.global-input { display: flex; align-items: center; gap: 8px; }
.global-input input { padding: 6px; border: 1px solid #ccc; border-radius: 4px; }
.gpa-display { background-color: #e9f7ef; border: 1px solid #a9d6b8; border-radius: 8px; padding: 16px; margin-bottom: 10px; display: flex; justify-content: space-around; font-size: 1.2em; }
.gpa-value { font-weight: bold; font-size: 1.5em; color: #28a745; }

.category-credits-display {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}
.category-credits-display h3 {
  margin-top: 0;
  margin-bottom: 12px;
  font-size: 1.1em;
  border-bottom: 1px solid #ccc;
  padding-bottom: 8px;
}
.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  /* 項目間の距離（特に左右）を広げる */
  gap: 8px 32px;
  font-size: 0.9em;
}
.category-item {
  display: flex;
  /* flex-startを指定して、左寄せにする */
  justify-content: flex-start;
  align-items: baseline;
  /* 項目内の名前と単位数の間の距離を指定 */
  gap: 0.8em;
}
.category-value {
  font-weight: bold;
  /* 個別のマージンは不要になったため削除 */
}

.table-header {
  display: grid;
  grid-template-columns: 80px 120px 100px 160px 1fr 120px 50px 80px;
  gap: 12px;
  font-weight: bold;
  border-bottom: 2px solid #333;
  padding: 0 4px 8px 4px;
  color: #555;
  font-size: 0.8em;
  text-align: center;
}
.col-info { text-align: left; }
</style>