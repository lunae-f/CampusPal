<script setup>
import { computed, watch, ref } from 'vue'

const props = defineProps({
  rowIndex: Number,
  rishunen: String,
  kougicd: String,
  evaluation: String,
  syllabusData: Object,
  isLoading: Boolean,
  error: String,
  isDuplicate: Boolean,
  isOlderAttempt: Boolean,
})
const emit = defineEmits([
  'update:rishunen',
  'update:kougicd',
  'update:evaluation',
  'fetch-request',
  'clear-row',
  'drag-start',
])

const debounceTimer = ref(null)

const isCodeInvalid = computed(() => {
  if (!props.kougicd) return false
  const regex = /^[a-z]{3}\d{6}$/i
  return !regex.test(props.kougicd)
})

const syllabusUrl = computed(() => {
  if (!props.rishunen || !props.kougicd) {
    return null
  }

  const params = new URLSearchParams({
    'value(risyunen)': props.rishunen,
    'value(semekikn)': '1',
    'value(kougicd)': props.kougicd,
  })
  return `https://websrv.tcu.ac.jp/tcu_web_v3/slbssbdr.do?${params.toString()}`
})

const fullInstructorText = computed(() => {
  if (!props.syllabusData?.instructors) return ''
  return Array.isArray(props.syllabusData.instructors)
    ? props.syllabusData.instructors.join(', ')
    : props.syllabusData.instructors
})
const displayInstructorText = computed(() => {
  const instructors = props.syllabusData?.instructors
  if (!Array.isArray(instructors) || instructors.length === 0) {
    return instructors || ''
  }
  if (instructors.length > 1) {
    return `${instructors[0]}　他`
  }
  return instructors[0]
})

watch([() => props.rishunen, () => props.kougicd], ([newYear, newCode], [oldYear, oldCode]) => {
  clearTimeout(debounceTimer.value)
  if (!newCode && oldCode) {
    emit('clear-row')
    return
  }
  if (newYear && newCode && !isCodeInvalid.value) {
    emit('fetch-request')
  }
})
</script>

<template>
  <div
    class="syllabus-row"
    :class="{
      'is-success': syllabusData,
      'is-error': error,
      'is-older-attempt': isOlderAttempt,
      'is-duplicate': isDuplicate,
    }"
  >
    <div class="col-handle" :draggable="true" @dragstart="$emit('drag-start')">
      <span class="drag-handle">⠿</span>
    </div>
    <div class="col-index">
      {{ rowIndex + 1 }}
    </div>
    <div class="col-year">
      <input
        :value="rishunen"
        @input="$emit('update:rishunen', $event.target.value)"
        placeholder="年度"
        class="input-field"
      />
    </div>
    <div class="col-code">
      <input
        :value="kougicd"
        @input="$emit('update:kougicd', $event.target.value)"
        placeholder="講義コード"
        class="input-field"
        :class="{ 'is-invalid': isCodeInvalid }"
        maxlength="9"
      />
    </div>
    <div class="col-term">
      <div class="term-year">{{ rishunen }}年度</div>
      <div>
        <span v-if="syllabusData">{{ syllabusData.term }}</span>
        <span v-else>&ndash;</span>
      </div>
    </div>
    <div class="col-info">
      <div v-if="isLoading" class="loading-text">検索中...</div>
      <div v-if="error" class="error-message">{{ error }}</div>
      <template v-if="syllabusData">
        <div class="course-name">
          <a :href="syllabusUrl" target="_blank" rel="noopener noreferrer">{{
            syllabusData.course_name
          }}</a>
        </div>
        <div class="course-details" data-label="学年">
          {{ syllabusData.student_year }}
        </div>
      </template>
    </div>
    <div class="col-instructors" :title="fullInstructorText" data-label="担当者">
      <span>{{ displayInstructorText }}</span>
    </div>
    <div class="col-credits" data-label="単位数">
      <span v-if="syllabusData?.credits">{{ syllabusData.credits }}</span>
    </div>
    <div class="col-eval" data-label="評価">
      <select
        :value="evaluation"
        @change="$emit('update:evaluation', $event.target.value)"
        class="input-field eval-select"
        :class="{ 'is-fail': evaluation === '不可' }"
      >
        <option value="">--</option>
        <option value="秀">秀</option>
        <option value="優">優</option>
        <option value="良">良</option>
        <option value="可">可</option>
        <option value="不可">不可</option>
      </select>
    </div>
  </div>
</template>

<style scoped>
/* デスクトップ用のスタイル */
.syllabus-row {
  display: grid;
  grid-template-columns: 30px 30px 60px 100px 100px 1fr 120px 50px 80px;
  gap: 12px;
  align-items: center;
  padding: 8px 4px;
  min-height: 50px;
  font-size: 0.9em;
  transition:
    background-color 0.3s,
    opacity 0.3s;
}
.col-index {
  text-align: center;
  color: #6c757d;
  font-size: 0.9em;
}
.drag-handle {
  cursor: grab;
  color: #3b3b3b8c;
  font-size: 1.5em;
  padding: 0 5px;
  text-decoration: none;
}
.drag-handle:active {
  cursor: grabbing;
}
.is-success {
  background-color: #e9f7ef;
}
.is-error {
  background-color: #fbe9e7;
}
.is-older-attempt {
  background-color: #aaadaf !important;
  opacity: 0.6;
}
.is-older-attempt > div:not(.col-handle):not(.col-index) {
  text-decoration: line-through;
}
.is-older-attempt:hover {
  opacity: 1;
}
.is-duplicate {
  background-color: #fff3e0 !important;
}
.col-year,
.col-code,
.col-info,
.col-instructors {
  text-align: left;
}
.col-credits,
.col-eval {
  text-align: center;
}
.col-term {
  text-align: center;
}
.term-year {
  font-size: 0.8em;
  color: #6c757d;
}
.input-field {
  padding: 6px;
  border: 1px solid #767676;
  border-radius: 4px;
  width: 100%;
  box-sizing: border-box;
}
.input-field.is-invalid {
  border-color: #d92c2c;
  box-shadow: 0 0 0 1px #d92c2c;
}
.input-field.is-fail {
  border-color: #d92c2c;
  color: #d92c2c;
  font-weight: bold;
}
.loading-text {
  font-size: 0.9em;
  color: #555;
}
.course-name {
  font-weight: bold;
}
.course-name a {
  color: inherit;
  text-decoration: none;
}
.course-name a:hover {
  text-decoration: underline;
  color: #0056b3;
}
.course-details {
  font-size: 0.9em;
  color: #555;
  margin-top: 4px;
}
.error-message {
  color: #d92c2c;
}

/* モバイル用のレイアウト */
@media (max-width: 1023px) {
  .syllabus-row {
    display: grid;
    grid-template-columns: auto repeat(11, 1fr); /* 12分割グリッド */
    gap: 8px 10px;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 8px;
    background-color: #fff;
  }

  .col-info {
    display: contents;
  }

  .col-handle {
    grid-area: 1 / 1 / 2 / 2;
  }
  .col-index {
    grid-area: 1 / 2 / 2 / 3;
    font-weight: bold;
  }
  .col-year {
    grid-area: 1 / 3 / 2 / 7;
  }
  .col-code {
    grid-area: 1 / 7 / 2 / 13;
  }
  .col-term {
    display: none;
  }

  .course-name {
    grid-area: 2 / 1 / 3 / 13;
  }

  /* ★ 修正箇所: 学年と担当者を3行目に並べて配置 */
  .course-details {
    grid-area: 3 / 1 / 4 / 7;
  }
  .col-instructors {
    grid-area: 3 / 7 / 4 / 13;
  }

  /* ★ 修正箇所: 評価と単位数を4行目に並べて配置 */
  .col-eval {
    grid-area: 4 / 1 / 5 / 7;
  }
  .col-credits {
    grid-area: 4 / 7 / 5 / 13;
  }

  .course-details,
  .col-instructors,
  .col-credits,
  .col-eval {
    padding: 0;
    border: none;
    text-align: left;
    font-size: 0.9em;
    min-height: 3.5em; /* ラベルと内容のための高さを確保 */
  }
  .course-details::before,
  .col-instructors::before,
  .col-credits::before,
  .col-eval::before {
    content: attr(data-label);
    font-size: 0.8em;
    color: #666;
    margin-bottom: 4px;
    display: block;
  }
}
</style>
