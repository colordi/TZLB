<script setup>
import { ref } from "vue";

const username = ref("");
const password = ref("");
const rememberSession = ref(true);
const showPassword = ref(false);
</script>

<template>
  <section class="design-login-page">
    <div class="design-login-decoration" aria-hidden="true">
      <span class="design-login-contour design-login-contour-one"></span>
      <span class="design-login-contour design-login-contour-two"></span>
      <span class="design-login-tree design-login-tree-one"></span>
      <span class="design-login-tree design-login-tree-two"></span>
    </div>

    <main class="design-login-shell">
      <form class="design-login-card" novalidate @submit.prevent>
        <header class="design-login-brand">
          <span class="design-login-brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.55">
              <path d="M12 3 7 10h3l-4 6h5v5h2v-5h5l-4-6h3Z" />
            </svg>
          </span>
          <p class="design-login-eyebrow">FORESTRY SURVEY</p>
          <h1>林业调查工作台</h1>
          <p class="design-login-intro">使用林业管理部门统一账号登录</p>
        </header>

        <div class="design-login-form">
          <div class="design-field">
            <label for="design-login-username">账号</label>
            <input
              id="design-login-username"
              v-model="username"
              class="design-input"
              name="username"
              autocomplete="username"
              placeholder="请输入账号"
              required
            />
          </div>

          <div class="design-field">
            <label for="design-login-password">密码</label>
            <div class="design-login-password-wrap">
              <input
                id="design-login-password"
                v-model="password"
                class="design-input"
                name="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="请输入密码"
                required
              />
              <button
                class="design-icon-button design-login-password-toggle"
                type="button"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                :aria-pressed="showPassword"
                @click="showPassword = !showPassword"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                  <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
                  <circle cx="12" cy="12" r="2.5" />
                  <path v-if="showPassword" d="m4 4 16 16" />
                </svg>
              </button>
            </div>
          </div>

          <div class="design-login-form-row">
            <label>
              <input v-model="rememberSession" type="checkbox" />
              <span>保持本次会话</span>
            </label>
            <span class="design-login-help">无法登录？</span>
          </div>

          <button class="design-button design-login-submit" type="submit">
            <span>进入工作台</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <path d="M5 12h14m-5-5 5 5-5 5" />
            </svg>
          </button>
        </div>

        <div class="design-login-security-note">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
            <path d="M12 3 5 6v5c0 4.8 2.8 8.1 7 10 4.2-1.9 7-5.2 7-10V6Z" />
            <path d="m9 12 2 2 4-4" />
          </svg>
          <span>系统将记录登录时间、设备与关键操作，用于安全审计和数据追溯。</span>
        </div>

        <p class="design-login-footnote">北京市林业资源调查与监测</p>
      </form>
    </main>
  </section>
</template>

<style src="../../styles/design-login.css"></style>
