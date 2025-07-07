<script setup>
// <script>セクションは変更ありません
import { computed, watch } from 'vue';
const props = defineProps({ rishunen: String, kougicd: String, evaluation: String, syllabusData: Object, isLoading: Boolean, error: String, isDuplicate: Boolean, isOlderAttempt: Boolean, crclumcd: String });
const emit = defineEmits(['update:rishunen', 'update:kougicd', 'update:evaluation', 'fetch-request', 'clear-row']);
const EVALUATION_SCORES = { '秀': 95, '優': 84.5, '良': 74.5, '可': 64.5, '不可': 0 };
const gradePoint = computed(() => { if (!props.evaluation) return null; if (props.evaluation === '不可') return 0; const score = EVALUATION_SCORES[props.evaluation]; if (score === undefined) return null; return (score - 50) / 10; });
const syllabusUrl = computed(() => { if (!props.rishunen || !props.kougicd || !props.crclumcd) return null; const params = new URLSearchParams({ 'value(risyunen)': props.rishunen, 'value(semekikn)': '1', 'value(kougicd)': props.kougicd, 'value(crclumcd)': props.crclumcd }); return `https://websrv.tcu.ac.jp/tcu_web_v3/slbssbdr.do?${params.toString()}`; });
const fullInstructorText = computed(() => { if (!props.syllabusData?.instructors) return ''; return Array.isArray(props.syllabusData.instructors) ? props.syllabusData.instructors.join(', ') : props.syllabusData.instructors; });
const displayInstructorText = computed(() => { const instructors = props.syllabusData?.instructors; if (!Array.isArray(instructors) || instructors.length === 0) return instructors || ''; if (instructors.length > 1) return `${instructors[0]}　他`; return instructors[0]; });
const isCodeInvalid = computed(() => { if (!props.kougicd) return false; const regex = /^[a-z]{3}\d{6}$/; return !regex.test(props.kougicd); });
watch(
  [() => props.rishunen, () => props.kougicd],
  ([newYear, newCode], [oldYear, oldCode]) => { if (newYear && newCode && !isCodeInvalid.value) { emit('fetch-request'); } else if (!newCode && oldCode) { emit('clear-row'); } }
);
</script>

<template>
  <div class="syllabus-row" :class="{ 'has-data': syllabusData, 'is-older-attempt': isOlderAttempt, 'is-duplicate': isDuplicate }">
    <div class="col-year"><input :value="rishunen" @input="$emit('update:rishunen', $event.target.value)" placeholder="年度" class="input-field" /></div>
    
    <div class="col-code"><input :value="kougicd" @input="$emit('update:kougicd', $event.target.value)" placeholder="講義コード" class="input-field" :class="{ 'is-invalid': isCodeInvalid }" /></div>

    <div class="col-term"><span v-if="syllabusData">{{ syllabusData.term }}</span><span v-else>&ndash;</span></div>

    <div class="col-category"><span v-if="syllabusData">{{ syllabusData.category }}</span></div>
    <div class="col-info">
       <div v-if="isLoading" class="loading-text">検索中...</div>
       <div v-if="error" class="error-message">エラー: {{ error }}</div>
       <div v-if="syllabusData">
        <div class="course-name"><a :href="syllabusUrl" target="_blank" rel="noopener noreferrer">{{ syllabusData.course_name }}</a></div>
        <div class="course-details">{{ syllabusData.department }} / {{ syllabusData.student_year }}</div>
      </div>
    </div>
    <div class="col-instructors" :title="fullInstructorText"><span>{{ displayInstructorText }}</span></div>
    <div class="col-credits"><span v-if="syllabusData?.credits">{{ syllabusData.credits }}</span></div>
    <div class="col-eval">
       <select :value="evaluation" @change="$emit('update:evaluation', $event.target.value)" class="input-field eval-select" :class="{ 'is-fail': evaluation === '不可' }">
        <option value="">--</option><option value="秀">秀</option><option value="優">優</option><option value="良">良</option><option value="可">可</option><option value="不可">不可</option>
      </select>
    </div>
  </div>
</template>

<style scoped>
.syllabus-row {
  display: grid;
  /* 2列目と3列目の幅を入れ替え */
  grid-template-columns: 80px 120px 100px 160px 1fr 120px 50px 80px;
  gap: 12px; align-items: center; border-bottom: 1px solid #eee; padding: 8px 4px; min-height: 50px; font-size: 0.9em;
  transition: background-color 0.3s, opacity 0.3s;
}
.has-data { background-color: #f9f9f9; }
.is-older-attempt {
  background-color: #aaadaf !important; /* 背景色を濃いグレーに変更 */
  opacity: 0.6; /* 透明度を少し調整 */
  text-decoration: line-through;
}
.is-older-attempt:hover { opacity: 1; }
.is-duplicate { background-color: #fff3e0 !important; }
.col-code { display: flex; gap: 8px; align-items: center; }
.col-info { min-width: 0; }
.col-category, .col-instructors { font-size: 0.9em; color: #555; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.col-credits { text-align: center; font-weight: bold; }
.input-field { padding: 6px; border: 1px solid #ccc; border-radius: 4px; width: 100%; box-sizing: border-box; }
.input-field.is-invalid { border-color: #dc3545; box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25); }
.input-field.is-fail { border-color: #dc3545; color: #dc3545; font-weight: bold; }
.loading-text { font-size: 0.9em; color: #555; }
.course-name { font-weight: bold; }
.course-name a { color: inherit; text-decoration: none; }
.course-name a:hover { text-decoration: underline; color: #0056b3; }
.course-details { font-size: 0.9em; color: #555; margin-top: 4px; }
.error-message { color: #d9534f; }
</style>