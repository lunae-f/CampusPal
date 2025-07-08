<script setup>
import { computed, watch, ref } from 'vue';

const props = defineProps({ rishunen: String, kougicd: String, evaluation: String, syllabusData: Object, isLoading: Boolean, error: String, isDuplicate: Boolean, isOlderAttempt: Boolean, crclumcd: String });
const emit = defineEmits(['update:rishunen', 'update:kougicd', 'update:evaluation', 'fetch-request', 'clear-row', 'focus-next']);

// 講義コードのinput要素への参照
const kougicdInput = ref(null);

// 親コンポーネントから呼び出されるフォーカス用のメソッド
const focusInput = () => {
  kougicdInput.value?.focus();
};
// 親にメソッドを公開
defineExpose({ focusInput });

const isCodeInvalid = computed(() => { if (!props.kougicd) return false; const regex = /^[a-z]{3}\d{6}$/; return !regex.test(props.kougicd); });
const syllabusUrl = computed(() => { if (!props.rishunen || !props.kougicd || !props.crclumcd) return null; const params = new URLSearchParams({ 'value(risyunen)': props.rishunen, 'value(semekikn)': '1', 'value(kougicd)': props.kougicd, 'value(crclumcd)': props.crclumcd }); return `https://websrv.tcu.ac.jp/tcu_web_v3/slbssbdr.do?${params.toString()}`; });
const fullInstructorText = computed(() => { if (!props.syllabusData?.instructors) return ''; return Array.isArray(props.syllabusData.instructors) ? props.syllabusData.instructors.join(', ') : props.syllabusData.instructors; });
const displayInstructorText = computed(() => { const instructors = props.syllabusData?.instructors; if (!Array.isArray(instructors) || instructors.length === 0) return instructors || ''; if (instructors.length > 1) return `${instructors[0]}　他`; return instructors[0]; });

watch(
  () => props.kougicd,
  (newCode) => {
    // 講義コードのwatchを、よりシンプルな単独のwatchに変更
    if (!isCodeInvalid.value) {
      emit('fetch-request');
      // コードが9桁になったら次の行へフォーカスを要求
      if (newCode && newCode.length === 9) {
        emit('focus-next');
      }
    } else if (!newCode) {
      emit('clear-row');
    }
  }
);
</script>

<template>
  <tr class="syllabus-row" :class="{ 'is-success': syllabusData, 'is-error': error, 'is-older-attempt': isOlderAttempt, 'is-duplicate': isDuplicate }">
    <td class="col-year">
      <input :value="rishunen" @input="$emit('update:rishunen', $event.target.value)" placeholder="年度" class="input-field" />
    </td>
    <td class="col-code">
      <input ref="kougicdInput" :value="kougicd" @input="$emit('update:kougicd', $event.target.value)" placeholder="講義コード" class="input-field" :class="{ 'is-invalid': isCodeInvalid }" maxlength="9" />
    </td>
    <td class="col-term">
      <span v-if="syllabusData">{{ syllabusData.term }}</span><span v-else>&ndash;</span>
    </td>
    <td class="col-category">
      <span v-if="syllabusData">{{ syllabusData.category }}</span>
    </td>
    <td class="col-info">
       <div v-if="isLoading" class="loading-text">検索中...</div>
       <div v-if="error" class="error-message">{{ error }}</div>
       <div v-if="syllabusData">
        <div class="course-name"><a :href="syllabusUrl" target="_blank" rel="noopener noreferrer">{{ syllabusData.course_name }}</a></div>
        <div class="course-details">{{ syllabusData.department }} / {{ syllabusData.student_year }}</div>
      </div>
    </td>
    <td class="col-instructors" :title="fullInstructorText"><span>{{ displayInstructorText }}</span></td>
    <td class="col-credits"><span v-if="syllabusData?.credits">{{ syllabusData.credits }}</span></td>
    <td class="col-eval">
       <select :value="evaluation" @change="$emit('update:evaluation', $event.target.value)" class="input-field eval-select" :class="{ 'is-fail': evaluation === '不可' }">
        <option value="">--</option><option value="秀">秀</option><option value="優">優</option><option value="良">良</option><option value="可">可</option><option value="不可">不可</option>
      </select>
    </td>
  </tr>
</template>


<style scoped>
.syllabus-row {
  display: grid;
  grid-template-columns: 60px 100px 100px 160px 1fr 120px 50px 80px;
  gap: 12px;
  align-items: center;
  border-bottom: 1px solid #eee;
  padding: 8px 4px;
  min-height: 50px;
  font-size: 0.9em;
  transition: background-color 0.3s, opacity 0.3s;
}
.is-success { background-color: #e9f7ef; }
.is-error { background-color: #fbe9e7; }
.is-older-attempt {
  background-color: #aaadaf !important;
  opacity: 0.6;
  text-decoration: line-through;
}
.is-older-attempt:hover { opacity: 1; }
.is-duplicate { background-color: #fff3e0 !important; }
.col-year, .col-code, .col-term, .col-category, .col-instructors {
  text-align: left;
}
.col-credits, .col-eval {
  text-align: center;
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
.loading-text { font-size: 0.9em; color: #555; }
.course-name { font-weight: bold; }
.course-name a { color: inherit; text-decoration: none; }
.course-name a:hover { text-decoration: underline; color: #0056b3; }
.course-details { font-size: 0.9em; color: #555; margin-top: 4px; }
.error-message {
  color: #d92c2c;
}
</style>