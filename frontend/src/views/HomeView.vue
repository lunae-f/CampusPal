<script setup>
import { ref, computed, onMounted, watch, onBeforeUpdate } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
import SyllabusRow from '../components/SyllabusRow.vue'
import { fetchSyllabus } from '../services/syllabusApi.js'

const STORAGE_KEY = 'gpa-calculator-data-v6' // バージョン更新
const EVALUATION_RANGES = {
  秀: { minScore: 90, maxScore: 100 },
  優: { minScore: 80, maxScore: 89 },
  良: { minScore: 70, maxScore: 79 },
  可: { minScore: 60, maxScore: 69 },
}
const rows = ref([])
const fileInput = ref(null)
const rowRefs = ref([])

// サイドバーの開閉状態
const isMobileSidebarOpen = ref(false)
const isFilterSidebarOpen = ref(true) // PC用フィルターサイドバー

const selectedYears = ref([])
const selectedTerms = ref([])
const selectedEvaluations = ref([])

const availableYears = computed(() =>
  [...new Set(rows.value.map((row) => row.rishunen).filter(Boolean))].sort((a, b) => b - a),
)
const availableTerms = computed(() =>
  [...new Set(rows.value.map((row) => row.syllabusData?.term).filter(Boolean))].sort(),
)
const availableEvaluations = ['秀', '優', '良', '可', '不可', '未評価']

const shouldShowRow = (row) => {
  const yearMatch =
    selectedYears.value.length === 0 || (row.rishunen && selectedYears.value.includes(row.rishunen))
  const termMatch =
    selectedTerms.value.length === 0 ||
    (row.syllabusData?.term && selectedTerms.value.includes(row.syllabusData.term))
  const evalMatch =
    selectedEvaluations.value.length === 0 ||
    (row.evaluation && selectedEvaluations.value.includes(row.evaluation)) ||
    (!row.evaluation && selectedEvaluations.value.includes('未評価'))

  return yearMatch && termMatch && evalMatch
}

onBeforeUpdate(() => {
  rowRefs.value = []
})

const onDragStart = (index) => {
  draggedIndex.value = index
}
const onDrop = (targetIndex) => {
  if (draggedIndex.value === null || draggedIndex.value === targetIndex) {
    draggedIndex.value = null
    return
  }
  const draggedItem = rows.value.splice(draggedIndex.value, 1)[0]
  rows.value.splice(targetIndex, 0, draggedItem)
  draggedIndex.value = null
}

const saveToFile = () => {
  try {
    const simplifiedRows = rows.value
      .filter((row) => row.kougicd)
      .map((row) => ({
        rishunen: row.rishunen,
        kougicd: row.kougicd,
        evaluation: row.evaluation || '',
      }))
    const dataToSave = { rows: simplifiedRows }
    const jsonString = JSON.stringify(dataToSave, null, 2)
    const blob = new Blob([jsonString], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'CampusPal_data.json'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (error) {
    alert('ファイルの保存に失敗しました。')
    console.error(error)
  }
}
const triggerFileInput = () => {
  fileInput.value.click()
}
const handleFileLoad = (event) => {
  const file = event.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const content = e.target.result
      let loadedData = {}
      if (file.name.endsWith('.csv')) {
        const lines = content.trim().split('\n')
        const simplifiedRows = []
        for (let i = 1; i < lines.length; i++) {
          const parts = lines[i].split(',')
          if (parts.length >= 3) {
            simplifiedRows.push({
              rishunen: parts[0].trim(),
              kougicd: parts[1].trim(),
              evaluation: parts[2].trim(),
            })
          }
        }
        loadedData = { rows: simplifiedRows }
      } else {
        loadedData = JSON.parse(content)
      }
      if (loadedData && Array.isArray(loadedData.rows)) {
        const newRows = loadedData.rows.map((simpleRow, index) => ({
          id: index,
          rishunen: simpleRow.rishunen,
          kougicd: simpleRow.kougicd,
          evaluation: simpleRow.evaluation,
          syllabusData: null,
          isLoading: false,
          error: null,
        }))
        rows.value = newRows
        fetchSyllabusDataForRows(rows.value)
        alert('データを読み込みました。')
      } else {
        throw new Error('ファイルの形式が正しくありません。')
      }
    } catch (error) {
      alert(`ファイルの読み込みに失敗しました: ${error.message}`)
      console.error(error)
    }
  }
  reader.readAsText(file)
  event.target.value = ''
}
const rowMetadata = computed(() => {
  const metadata = {}
  const kougicdCounts = {}
  const coursesByName = {}
  rows.value.forEach((row) => {
    metadata[row.id] = { isDuplicate: false, isOlderAttempt: false }
    if (row.kougicd) {
      kougicdCounts[row.kougicd] = (kougicdCounts[row.kougicd] || 0) + 1
    }
    if (row.syllabusData?.course_name) {
      const name = row.syllabusData.course_name
      if (!coursesByName[name]) coursesByName[name] = []
      coursesByName[name].push(row)
    }
  })
  rows.value.forEach((row) => {
    if (row.kougicd && kougicdCounts[row.kougicd] > 1) {
      metadata[row.id].isDuplicate = true
    }
  })
  const getTermRank = (term) => {
    const order = { 前期前半: 1, 前期後半: 2, 前期: 3, 後期前半: 4, 後期後半: 5, 後期: 6 }
    return order[term] || 0
  }
  for (const courseName in coursesByName) {
    const group = coursesByName[courseName]
    if (group.length > 1) {
      group.sort((a, b) => {
        if (a.rishunen !== b.rishunen) return b.rishunen - a.rishunen
        const rankA = getTermRank(a.syllabusData.term)
        const rankB = getTermRank(b.syllabusData.term)
        return rankB - rankA
      })
      for (let i = 1; i < group.length; i++) {
        metadata[group[i].id].isOlderAttempt = true
      }
    }
  }
  return metadata
})
const finalRowsForCalc = computed(() => {
  return rows.value.filter(
    (row) =>
      row.kougicd && row.syllabusData?.course_name && !rowMetadata.value[row.id]?.isOlderAttempt,
  )
})
const gpaStats = computed(() => {
  let totalMinGpProduct = 0,
    totalMaxGpProduct = 0,
    totalAttemptedCredits = 0,
    totalEarnedCredits = 0,
    totalInProgressCredits = 0
  for (const row of finalRowsForCalc.value) {
    const credits = Number(row.syllabusData?.credits)
    if (!credits) continue
    if (row.evaluation) {
      totalAttemptedCredits += credits
      let minGp = 0,
        maxGp = 0
      if (row.evaluation !== '不可') {
        const range = EVALUATION_RANGES[row.evaluation]
        if (range) {
          minGp = (range.minScore - 50) / 10
          maxGp = (range.maxScore - 50) / 10
        }
        totalEarnedCredits += credits
      }
      totalMinGpProduct += minGp * credits
      totalMaxGpProduct += maxGp * credits
    } else {
      totalInProgressCredits += credits
    }
  }
  const minGpa = totalAttemptedCredits > 0 ? totalMinGpProduct / totalAttemptedCredits : 0
  const maxGpa = totalAttemptedCredits > 0 ? totalMaxGpProduct / totalAttemptedCredits : 0
  const avgGpa = (minGpa + maxGpa) / 2
  const currentRate =
    totalAttemptedCredits > 0 ? (totalEarnedCredits / totalAttemptedCredits) * 100 : 0
  const prospectiveTotalAttempted = totalAttemptedCredits + totalInProgressCredits
  const prospectiveTotalEarned = totalEarnedCredits + totalInProgressCredits
  const prospectiveRate =
    prospectiveTotalAttempted > 0 ? (prospectiveTotalEarned / prospectiveTotalAttempted) * 100 : 0
  return {
    totalAttemptedCredits,
    totalEarnedCredits,
    totalInProgressCredits,
    currentRate: currentRate.toFixed(1),
    prospectiveRate: prospectiveRate.toFixed(1),
    minGpa: minGpa.toFixed(3),
    maxGpa: maxGpa.toFixed(3),
    avgGpa: avgGpa.toFixed(3),
  }
})

const groupedAndSortedCreditsByTerm = computed(() => {
  const termTotals = {}
  for (const row of finalRowsForCalc.value) {
    if (row.rishunen && row.syllabusData?.term && row.syllabusData?.credits) {
      const termKey = `${row.rishunen}年度 ${row.syllabusData.term}`
      if (!termTotals[termKey]) {
        termTotals[termKey] = { earned: 0, attempted: 0, inProgress: 0 }
      }
      const credits = Number(row.syllabusData.credits)
      if (row.evaluation) {
        termTotals[termKey].attempted += credits
        if (row.evaluation !== '不可') {
          termTotals[termKey].earned += credits
        }
      } else {
        termTotals[termKey].inProgress += credits
      }
    }
  }
  const grouped = {}
  const termOrder = [
    '通年',
    '前期',
    '前期前半',
    '前期後半',
    '後期',
    '後期後半',
    '通年（卒研）',
    '集中（前期）',
    '集中（後期）',
    '集中（通年）',
    '通年（事例）',
    '通年（大学院）',
  ]
  const getOrderIndex = (termName) => {
    const index = termOrder.indexOf(termName)
    return index === -1 ? Infinity : index
  }
  for (const fullTermKey in termTotals) {
    const parts = fullTermKey.split('年度 ')
    const year = parts[0]
    const termName = parts[1]
    if (!grouped[year]) {
      grouped[year] = { terms: [], yearStats: { earned: 0, attempted: 0, inProgress: 0 } }
    }
    const termStat = termTotals[fullTermKey]
    grouped[year].terms.push({ termName: termName, stats: termStat })
    grouped[year].yearStats.earned += termStat.earned
    grouped[year].yearStats.attempted += termStat.attempted
    grouped[year].yearStats.inProgress += termStat.inProgress
  }
  for (const year in grouped) {
    grouped[year].terms.sort((a, b) => getOrderIndex(a.termName) - getOrderIndex(b.termName))
  }
  return Object.keys(grouped)
    .sort((a, b) => a - b)
    .map((year) => ({ year: year, ...grouped[year] }))
})
const handleFetch = async (row) => {
  row.isLoading = true
  row.error = null
  try {
    const data = await fetchSyllabus({
      kougicd: row.kougicd,
      rishunen: row.rishunen,
    })
    row.syllabusData = data
  } catch (e) {
    row.error = e.message
    row.syllabusData = null
  } finally {
    row.isLoading = false
  }
}
const fetchSyllabusDataForRows = async (rowsToFetch) => {
  for (const row of rowsToFetch) {
    if (row.kougicd && row.rishunen) {
      await handleFetch(row)
    }
  }
}
const addNewRow = () => {
  const lastRow = rows.value.length > 0 ? rows.value[rows.value.length - 1] : null
  const newYear = lastRow ? lastRow.rishunen : '2024'
  rows.value.push({
    id: rows.value.length,
    rishunen: newYear,
    kougicd: '',
    evaluation: '',
    syllabusData: null,
    isLoading: false,
    error: null,
  })
}
const clearRowData = (rowToClear) => {
  rowToClear.evaluation = ''
  rowToClear.syllabusData = null
  rowToClear.isLoading = false
  rowToClear.error = null
}
onMounted(() => {
  const savedDataString = localStorage.getItem(STORAGE_KEY)
  if (savedDataString) {
    try {
      const savedData = JSON.parse(savedDataString)
      if (savedData.rows.length > 0) {
        const newRows = savedData.rows.map((simpleRow, index) => ({
          id: index,
          rishunen: simpleRow.rishunen,
          kougicd: simpleRow.kougicd,
          evaluation: simpleRow.evaluation,
          syllabusData: null,
          isLoading: false,
          error: null,
        }))
        rows.value = newRows
        fetchSyllabusDataForRows(rows.value)
        return
      }
    } catch (e) {
      console.error('Failed to parse localStorage data:', e)
      localStorage.removeItem(STORAGE_KEY)
    }
  }
  rows.value = Array.from({ length: 15 }, (_, i) => ({
    id: i,
    rishunen: '2024',
    kougicd: '',
    evaluation: '',
    syllabusData: null,
    isLoading: false,
    error: null,
  }))
})
watch(
  rows,
  (newRows) => {
    const simplifiedRows = newRows
      .filter((row) => row.kougicd)
      .map((row) => ({
        rishunen: row.rishunen,
        kougicd: row.kougicd,
        evaluation: row.evaluation || '',
      }))
    const dataToSave = { rows: simplifiedRows }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(dataToSave))
    if (newRows.length > 0) {
      const lastRow = newRows[newRows.length - 1]
      if (lastRow.kougicd || lastRow.evaluation) {
        addNewRow()
      }
    }
  },
  { deep: true },
)
</script>

<template>
  <div>
    <!-- 新しいルート要素 -->
    <header class="header">
      <div class="header-inner">
        <div class="header-left">
          <button @click="isFilterSidebarOpen = !isFilterSidebarOpen" class="filter-toggle-button">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="9" y1="3" x2="9" y2="21"></line>
            </svg>
          </button>
          <h1>CampusPal</h1>
        </div>
        <div class="header-controls">
          <div class="file-operations">
            <button @click="saveToFile" class="io-button">ファイルに保存</button>
            <button @click="triggerFileInput" class="io-button">ファイルから読込</button>
            <input
              type="file"
              ref="fileInput"
              @change="handleFileLoad"
              accept=".json,.csv"
              style="display: none"
            />
          </div>
        </div>
        <!-- モバイル用サイドバー開閉ボタン -->
        <button @click="isMobileSidebarOpen = true" class="mobile-sidebar-toggle">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
      </div>
    </header>

    <div class="page-content">
      <!-- PC用フィルターサイドバー -->
      <aside class="filter-sidebar" :class="{ 'is-closed': !isFilterSidebarOpen }">
        <section class="filter-controls">
          <h3>絞り込み</h3>
          <div class="filter-group">
            <label>年度</label>
            <div class="checkbox-group">
              <div v-for="year in availableYears" :key="year" class="checkbox-item">
                <input type="checkbox" :id="`year-${year}`" :value="year" v-model="selectedYears" />
                <label :for="`year-${year}`">{{ year }}</label>
              </div>
            </div>
          </div>
          <div class="filter-group">
            <label>開講時期</label>
            <div class="checkbox-group">
              <div v-for="term in availableTerms" :key="term" class="checkbox-item">
                <input type="checkbox" :id="`term-${term}`" :value="term" v-model="selectedTerms" />
                <label :for="`term-${term}`">{{ term }}</label>
              </div>
            </div>
          </div>
          <div class="filter-group">
            <label>評価</label>
            <div class="checkbox-group">
              <div v-for="ev in availableEvaluations" :key="ev" class="checkbox-item">
                <input
                  type="checkbox"
                  :id="`eval-${ev}`"
                  :value="ev"
                  v-model="selectedEvaluations"
                />
                <label :for="`eval-${ev}`">{{ ev }}</label>
              </div>
            </div>
          </div>
        </section>
      </aside>

      <div class="container">
        <!-- 2カラムレイアウトのラッパー -->
        <div class="layout-wrapper">
          <!-- メインコンテンツ（左カラム） -->
          <main class="main-content">
            <!-- モバイル用フィルターUI -->
            <section class="mobile-filter-controls">
              <details class="filter-details">
                <summary>絞り込み</summary>
                <div class="filter-options">
                  <div class="filter-group">
                    <label>年度</label>
                    <div class="checkbox-group">
                      <div
                        v-for="year in availableYears"
                        :key="`mobile-year-${year}`"
                        class="checkbox-item"
                      >
                        <input
                          type="checkbox"
                          :id="`mobile-year-${year}`"
                          :value="year"
                          v-model="selectedYears"
                        />
                        <label :for="`mobile-year-${year}`">{{ year }}</label>
                      </div>
                    </div>
                  </div>
                  <div class="filter-group">
                    <label>開講時期</label>
                    <div class="checkbox-group">
                      <div
                        v-for="term in availableTerms"
                        :key="`mobile-term-${term}`"
                        class="checkbox-item"
                      >
                        <input
                          type="checkbox"
                          :id="`mobile-term-${term}`"
                          :value="term"
                          v-model="selectedTerms"
                        />
                        <label :for="`mobile-term-${term}`">{{ term }}</label>
                      </div>
                    </div>
                  </div>
                  <div class="filter-group">
                    <label>評価</label>
                    <div class="checkbox-group">
                      <div
                        v-for="ev in availableEvaluations"
                        :key="`mobile-eval-${ev}`"
                        class="checkbox-item"
                      >
                        <input
                          type="checkbox"
                          :id="`mobile-eval-${ev}`"
                          :value="ev"
                          v-model="selectedEvaluations"
                        />
                        <label :for="`mobile-eval-${ev}`">{{ ev }}</label>
                      </div>
                    </div>
                  </div>
                </div>
              </details>
            </section>

            <div class="table-header">
              <div class="col-handle"></div>
              <div class="col-index">#</div>
              <div class="col-year">年度</div>
              <div class="col-code">講義コード</div>
              <div class="col-term">学期</div>
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
              <div
                v-for="(row, index) in rows"
                :key="row.id"
                class="drag-wrapper"
                v-show="shouldShowRow(row)"
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
                  @fetch-request="handleFetch(row)"
                  @clear-row="clearRowData(row)"
                  @drag-start="onDragStart(index)"
                />
              </div>
            </VueDraggable>
          </main>

          <!-- サイドバー（右カラム） -->
          <aside class="sidebar" :class="{ 'mobile-is-open': isMobileSidebarOpen }">
            <button @click="isMobileSidebarOpen = false" class="mobile-sidebar-close">
              &times;
            </button>
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
                  <span class="in-progress-credits" v-if="gpaStats.totalInProgressCredits > 0"
                    >(+{{ gpaStats.totalInProgressCredits }})</span
                  >
                </div>
                <div class="gpa-range">
                  取得率: {{ gpaStats.currentRate }}%
                  <span v-if="gpaStats.totalInProgressCredits > 0"
                    >({{ gpaStats.prospectiveRate }}%)</span
                  >
                </div>
              </div>
            </section>
            <div class="stats-container">
              <section class="term-credits-display">
                <h3>単位数（開講時期別）</h3>
                <div class="term-grid">
                  <div
                    v-for="group in groupedAndSortedCreditsByTerm"
                    :key="group.year"
                    class="year-group"
                  >
                    <div class="year-header">
                      <h4>{{ group.year }}年度</h4>
                      <span class="year-total"
                        >{{ group.yearStats.earned }} / {{ group.yearStats.attempted }}
                        <span class="in-progress-credits" v-if="group.yearStats.inProgress > 0"
                          >(+{{ group.yearStats.inProgress }})</span
                        >
                        単位</span
                      >
                    </div>
                    <div v-for="item in group.terms" :key="item.termName" class="term-item">
                      <span class="term-name">{{ item.termName }}</span>
                      <span class="term-value"
                        >{{ item.stats.earned }} / {{ item.stats.attempted }}
                        <span class="in-progress-credits" v-if="item.stats.inProgress > 0"
                          >(+{{ item.stats.inProgress }})</span
                        >
                        単位</span
                      >
                    </div>
                  </div>
                </div>
              </section>
            </div>
          </aside>
        </div>
        <!-- オーバーレイ -->
        <div
          v-if="isMobileSidebarOpen"
          @click="isMobileSidebarOpen = false"
          class="sidebar-overlay"
        ></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* PC用のスタイル */
.page-content {
  display: flex;
}
.container {
  padding: 20px;
  font-family: sans-serif;
  max-width: 1600px;
  margin: 0 auto;
  flex-grow: 1; /* コンテンツエリアが残りのスペースを埋めるように */
  transition: margin-left 0.3s ease-in-out;
}

.header {
  position: sticky;
  top: 0;
  z-index: 990;
  background-color: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.header-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  max-width: 1600px;
  margin: 0 auto;
  padding: 10px 20px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}
.file-operations {
  display: flex;
  gap: 8px;
}
.io-button {
  padding: 6px 12px;
  border: 1px solid #6c757d;
  background-color: #fff;
  color: #6c757d;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
}
.io-button:hover {
  background-color: #f8f9fa;
}
.global-input {
  display: flex;
  align-items: center;
  gap: 8px;
}
.global-input input {
  padding: 6px;
  border: 1px solid #ccc;
  border-radius: 4px;
  width: 120px;
}
.tooltip-label {
  cursor: help;
  border-bottom: 1px dotted #6c757d;
}
.gpa-display {
  background-color: #e9f7ef;
  border: 1px solid #a9d6b8;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  justify-content: space-around;
  flex-wrap: wrap;
  gap: 15px;
}
.gpa-item {
  text-align: center;
}
.gpa-label {
  font-size: 0.9em;
  color: #333;
}
.gpa-main-value {
  font-weight: bold;
  font-size: 2em;
  color: #00754a;
  line-height: 1.2;
}
.gpa-range {
  font-size: 0.8em;
  color: #6c757d;
}
.in-progress-credits {
  font-size: 0.8em;
  color: #00754a;
}
.stats-container {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}
.term-credits-display {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 16px;
}
.term-credits-display h3 {
  margin-top: 0;
  margin-bottom: 12px;
  font-size: 1.1em;
  border-bottom: 1px solid #ccc;
  padding-bottom: 8px;
}
.term-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.year-group {
}
.year-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-size: 1em;
  font-weight: bold;
  margin: 0 0 8px 0;
  padding-bottom: 4px;
  border-bottom: 1px solid #e0e0e0;
}
.year-header h4 {
  margin: 0;
}
.year-total {
  font-size: 0.9em;
  font-weight: normal;
  color: #555;
}
.term-item {
  display: flex;
  justify-content: space-between;
  padding-left: 10px;
  padding-bottom: 4px;
  font-size: 0.9em;
}
.term-value {
  font-weight: bold;
}

.filter-controls {
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding: 15px;
}
.filter-controls h3 {
  margin: 0 0 10px 0;
  font-size: 1.2em;
}
.filter-group {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}
.filter-group label {
  font-size: 1em;
  font-weight: bold;
}
.checkbox-group {
  max-height: 180px;
  overflow-y: auto;
  border: 1px solid #e0e0e0;
  padding: 8px;
  border-radius: 4px;
  width: 100%;
  background-color: #fff;
  box-sizing: border-box;
}
.checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px;
}
.checkbox-item input[type='checkbox'] {
  width: auto;
  flex-shrink: 0;
}
.checkbox-item label {
  font-weight: normal;
  white-space: normal;
}

.table-header {
  display: grid;
  grid-template-columns: 30px 30px 60px 100px 100px 1fr 120px 50px 80px;
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
.table-header .col-instructors {
  text-align: left;
}
.drag-wrapper {
  border-bottom: 1px solid #eee;
}
.draggable-ghost {
  opacity: 0.5;
  background: #cce5ff;
}

/* --- Sidebar Styles --- */
.mobile-sidebar-toggle {
  display: none;
}
.mobile-sidebar-close {
  display: none;
}
.filter-toggle-button {
  display: none;
}
.mobile-filter-controls {
  display: none;
}

/* --- 2カラムレイアウト用のスタイル --- */
@media (min-width: 1024px) {
  .filter-sidebar {
    width: 260px;
    transition: margin-left 0.3s ease-in-out;
    background-color: #f8f9fa;
    border-right: 1px solid #e0e0e0;
    height: calc(100vh - 65px); /* ヘッダーの高さを引く */
    position: sticky;
    top: 65px; /* ヘッダーの高さ分下げる */
    overflow-y: auto;
    flex-shrink: 0;
  }
  .filter-sidebar.is-closed {
    margin-left: -260px;
  }
  .filter-toggle-button {
    display: block;
    background: none;
    border: none;
    cursor: pointer;
    padding: 8px;
  }
  .layout-wrapper {
    display: grid;
    grid-template-columns: 3.3027756377fr 1fr;
    gap: 24px;
  }
  .sidebar {
    position: sticky;
    top: 85px; /* ヘッダー + コンテナのpadding */
    align-self: start;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  .stats-container {
    grid-template-columns: 1fr;
  }
  .gpa-display {
    margin-bottom: 0; /* gapで制御するため不要に */
  }
}

/* --- Mobile View --- */
@media (max-width: 1023px) {
  .page-content {
    display: block;
  }
  .filter-sidebar {
    display: none;
  }
  .mobile-filter-controls {
    display: block;
    margin-bottom: 10px;
  }
  .filter-details {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
  }
  .filter-details summary {
    padding: 12px;
    font-weight: bold;
    cursor: pointer;
  }
  .filter-options {
    padding: 0 12px 12px 12px;
  }
  .filter-controls {
    padding: 0;
  }
  .filter-group {
    margin-top: 10px;
  }
  .checkbox-group {
    max-height: 150px;
  }

  .container {
    padding: 10px;
  }
  .header-inner {
    flex-wrap: nowrap;
    justify-content: space-between;
    padding: 10px;
  }
  .header-inner h1 {
    font-size: 1.2em;
  }
  .header-controls {
    display: none;
  }
  .mobile-sidebar-toggle {
    display: block;
    background: none;
    border: none;
    cursor: pointer;
    padding: 8px;
  }
  .layout-wrapper {
    display: block;
  }
  .sidebar {
    position: fixed;
    top: 0;
    right: 0;
    width: 85%;
    max-width: 320px;
    height: 100vh;
    background-color: #ffffff;
    box-shadow: -3px 0 15px rgba(0, 0, 0, 0.2);
    transform: translateX(100%);
    transition: transform 0.3s ease-in-out;
    z-index: 1000;
    padding: 20px;
    padding-top: 50px;
    overflow-y: auto;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  .sidebar.mobile-is-open {
    transform: translateX(0);
  }
  .mobile-sidebar-close {
    display: block;
    position: absolute;
    top: 10px;
    right: 15px;
    font-size: 2.5em;
    line-height: 1;
    background: none;
    border: none;
    cursor: pointer;
    color: #888;
  }
  .sidebar-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.6);
    z-index: 999;
    transition: opacity 0.3s ease-in-out;
  }
  .stats-container {
    grid-template-columns: 1fr;
  }
  .table-header {
    display: none;
  }
  .syllabus-table {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .drag-wrapper {
    border: 1px solid #ddd;
    border-radius: 8px;
    background-color: #fff;
  }
}
</style>
