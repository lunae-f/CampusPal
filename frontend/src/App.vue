<script setup>
import { ref } from 'vue';
import { RouterView } from 'vue-router'

// モーダルの表示状態を管理するリアクティブ変数
const isLicenseVisible = ref(false);
</script>

<template>
  <div class="app-wrapper">
    <RouterView />
    <footer class="app-footer">
      <a href="https://github.com/lunae-f/CampusPal" target="_blank" rel="noopener noreferrer">CampusPal</a>, 
      made with ❤️‍🔥 by Lunae. | 
      <!-- リンクテキストを変更し、クリックでモーダルを表示 -->
      <a href="#" @click.prevent="isLicenseVisible = true" class="footer-link">Licenses</a>
    </footer>

    <!-- ライセンス表示用モーダル -->
    <div v-if="isLicenseVisible" class="modal-overlay" @click.self="isLicenseVisible = false">
      <div class="modal-content">
        <button @click="isLicenseVisible = false" class="close-button">&times;</button>
        <h2>Licenses</h2>

        <h3>CampusPal</h3>
        <pre class="license-text">
MIT License

Copyright (c) 2025 Lunae

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
        </pre>

        <h3>vue-draggable-plus</h3>
        <pre class="license-text">
MIT License

Copyright (c) 2023 丶远方

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
        </pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-wrapper {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
:deep(main) {
  flex-grow: 1;
}
.app-footer {
  flex-shrink: 0;
  text-align: center;
  padding: 20px;
  margin-top: 40px;
  font-size: 0.9em;
  color: #6c757d;
  border-top: 1px solid #eee;
}
.app-footer a {
  color: #0056b3;
  text-decoration: none;
}
.app-footer a:hover {
  text-decoration: underline;
}
.footer-link {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
}

/* --- モーダル用のスタイル --- */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.modal-content {
  background-color: #fff;
  padding: 20px 30px;
  border-radius: 8px;
  width: 90%;
  max-width: 800px;
  max-height: 80vh;
  overflow-y: auto;
  position: relative;
}
.close-button {
  position: absolute;
  top: 10px;
  right: 15px;
  background: none;
  border: none;
  font-size: 2rem;
  color: #aaa;
  cursor: pointer;
}
.close-button:hover {
  color: #333;
}
.modal-content h2 {
  margin-top: 0;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
  margin-bottom: 20px;
}
.modal-content h3 {
  margin-top: 20px;
  margin-bottom: 10px;
}
.license-text {
  white-space: pre-wrap;
  font-family: monospace;
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  padding: 15px;
  border-radius: 4px;
  font-size: 0.8em;
  line-height: 1.6;
}
</style>
