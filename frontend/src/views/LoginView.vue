<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useToast } from "../composables/useToast.js";
import { signIn } from "../composables/useAuthSession.js";

const REMEMBERED_USERNAME_KEY = "tzlb.rememberedUsername";

const router = useRouter();
const route = useRoute();
const { error, info, success } = useToast();

const username = ref("");
const password = ref("");
const rememberMe = ref(false);
const showPassword = ref(false);
const submitting = ref(false);

const targetPath = computed(() => {
  const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "";
  if (redirect.startsWith("/") && redirect !== "/login") {
    return redirect;
  }
  return "/map";
});

function readRememberedUsername() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(REMEMBERED_USERNAME_KEY) || "";
}

function persistRememberedUsername(value) {
  if (typeof window === "undefined") {
    return;
  }

  if (rememberMe.value) {
    window.localStorage.setItem(REMEMBERED_USERNAME_KEY, value);
    return;
  }

  window.localStorage.removeItem(REMEMBERED_USERNAME_KEY);
}

function handleForgotPassword() {
  info("请联系系统管理员协助重置密码。", "忘记密码");
}

function handleRequestAccess() {
  info("请联系林业调查局管理员申请账号开通。", "申请加入");
}

async function handleSubmit() {
  const normalizedUsername = username.value.trim();
  const normalizedPassword = password.value.trim();

  if (!normalizedUsername || !normalizedPassword) {
    error("请输入完整的用户名和密码后再继续。", "登录信息不完整");
    return;
  }

  submitting.value = true;

  try {
    await signIn({
      username: normalizedUsername,
      password: normalizedPassword,
      remember_me: rememberMe.value,
    });
    persistRememberedUsername(normalizedUsername);
    success(`欢迎回来，${normalizedUsername}。`, "登录成功");
    await router.push(targetPath.value);
  } catch (submitError) {
    error(`${submitError.message || submitError}`, "登录失败");
  } finally {
    submitting.value = false;
  }
}

onMounted(() => {
  const rememberedUsername = readRememberedUsername();
  if (!rememberedUsername) {
    return;
  }

  username.value = rememberedUsername;
  rememberMe.value = true;
});
</script>

<template>
  <section class="login-page" data-testid="login-page">
    <div class="login-decoration" aria-hidden="true">
      <span class="login-contour login-contour-one"></span>
      <span class="login-contour login-contour-two"></span>
      <span class="login-tree login-tree-one"></span>
      <span class="login-tree login-tree-two"></span>
    </div>

    <main class="login-shell">
      <form class="login-card" novalidate @submit.prevent="handleSubmit">
        <header class="login-brand">
          <span class="login-brand__mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.55">
              <path d="M12 3 7 10h3l-4 6h5v5h2v-5h5l-4-6h3Z" />
            </svg>
          </span>
          <p class="login-eyebrow">FORESTRY SURVEY</p>
          <h1 class="login-brand__title">林业调查工作台</h1>
          <p class="login-brand__subtitle">使用林业管理部门统一账号登录</p>
        </header>

        <div class="login-form">
          <label class="login-field" for="login-username">
            <span>账号</span>
            <span class="login-input-frame">
              <input
                id="login-username"
                v-model.trim="username"
                :disabled="submitting"
                autocomplete="username"
                name="username"
                placeholder="请输入账号"
                required
                type="text"
              />
            </span>
          </label>

          <label class="login-field" for="login-password">
            <span>密码</span>
            <span class="login-input-frame login-password-frame">
              <input
                id="login-password"
                v-model.trim="password"
                :disabled="submitting"
                autocomplete="current-password"
                name="password"
                placeholder="请输入密码"
                required
                :type="showPassword ? 'text' : 'password'"
              />
              <button
                class="login-password-toggle"
                type="button"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                :aria-pressed="showPassword"
                :disabled="submitting"
                @click="showPassword = !showPassword"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                  <path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z" />
                  <circle cx="12" cy="12" r="2.5" />
                  <path v-if="showPassword" d="m4 4 16 16" />
                </svg>
              </button>
            </span>
          </label>

          <div class="login-options">
            <label class="login-checkbox" for="remember-me">
              <input
                id="remember-me"
                v-model="rememberMe"
                :disabled="submitting"
                type="checkbox"
              />
              <span>记住我</span>
            </label>

            <button
              type="button"
              class="login-link"
              :disabled="submitting"
              @click="handleForgotPassword"
            >
              忘记密码？
            </button>
          </div>

          <button type="submit" class="login-submit" :disabled="submitting">
            <span>{{ submitting ? "正在进入" : "进入工作台" }}</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
              <path d="M5 12h14m-5-5 5 5-5 5" />
            </svg>
          </button>
        </div>

        <div class="login-security-note">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
            <path d="M12 3 5 6v5c0 4.8 2.8 8.1 7 10 4.2-1.9 7-5.2 7-10V6Z" />
            <path d="m9 12 2 2 4-4" />
          </svg>
          <span>系统将记录登录时间、设备与关键操作，用于安全审计和数据追溯。</span>
        </div>

        <div class="login-card__foot">
          <p>
            还没有账号？
            <button
              type="button"
              class="login-link login-link--accent"
              :disabled="submitting"
              @click="handleRequestAccess"
            >
              申请加入
            </button>
          </p>
        </div>

        <p class="login-footnote">北京市林业资源调查与监测</p>
      </form>
    </main>
  </section>
</template>

<style scoped>
.login-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  font-family: var(--font-body);
  background: color-mix(in oklch, var(--color-bg) 68%, var(--color-primary-container));
}

.login-shell {
  isolation: isolate;
  position: relative;
  z-index: 1;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(24px, 6vw, 72px) var(--space-5);
  background:
    linear-gradient(color-mix(in oklch, var(--color-primary) 4%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in oklch, var(--color-primary) 4%, transparent) 1px, transparent 1px),
    radial-gradient(circle at 50% 36%, var(--color-surface) 0, transparent 48%);
  background-size: 48px 48px, 48px 48px, auto;
}

.login-decoration {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

.login-contour {
  position: absolute;
  width: clamp(320px, 44vw, 760px);
  aspect-ratio: 1;
  border: 1px solid color-mix(in oklch, var(--color-primary) 16%, transparent);
  border-radius: 43% 57% 38% 62% / 52% 38% 62% 48%;
}

.login-contour::before,
.login-contour::after {
  position: absolute;
  border: inherit;
  border-radius: inherit;
  content: "";
}

.login-contour::before {
  inset: 8%;
  transform: rotate(12deg);
}

.login-contour::after {
  inset: 18%;
  transform: rotate(-8deg);
}

.login-contour-one {
  top: -20%;
  right: -13%;
  transform: rotate(18deg);
}

.login-contour-two {
  bottom: -27%;
  left: -15%;
  transform: rotate(-24deg);
}

.login-tree {
  position: absolute;
  width: 18px;
  height: 24px;
  color: color-mix(in oklch, var(--color-primary) 24%, transparent);
}

.login-tree::before,
.login-tree::after {
  position: absolute;
  left: 50%;
  content: "";
  transform: translateX(-50%);
}

.login-tree::before {
  top: 0;
  width: 0;
  height: 0;
  border-right: 9px solid transparent;
  border-bottom: 17px solid currentColor;
  border-left: 9px solid transparent;
}

.login-tree::after {
  bottom: 0;
  width: 1px;
  height: 9px;
  background: currentColor;
}

.login-tree-one {
  top: 18%;
  left: 13%;
  transform: scale(0.82);
}

.login-tree-two {
  right: 16%;
  bottom: 17%;
  transform: scale(1.1);
}

.login-card {
  position: relative;
  width: min(420px, 100%);
  padding: clamp(26px, 5vw, 38px);
  border: 1px solid color-mix(in oklch, var(--color-primary) 18%, var(--color-border));
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  box-shadow: 0 24px 70px color-mix(in oklch, var(--color-nav) 13%, transparent);
  animation: login-enter 520ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

.login-card::before {
  position: absolute;
  top: 0;
  left: 50%;
  width: 68px;
  height: 3px;
  border-radius: 0 0 3px 3px;
  background: var(--color-primary);
  content: "";
  transform: translateX(-50%);
}

.login-brand {
  display: grid;
  justify-items: center;
  margin-bottom: 28px;
  text-align: center;
}

.login-brand__mark {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  margin-bottom: 15px;
  border: 1px solid color-mix(in oklch, var(--color-primary) 22%, var(--color-border));
  border-radius: var(--radius-round);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.login-brand__mark svg {
  width: 25px;
  height: 25px;
}

.login-eyebrow {
  margin-bottom: 7px;
  color: var(--color-primary);
  font-family: var(--font-mono);
  font-size: var(--text-2xs);
  font-weight: 700;
  letter-spacing: 0.16em;
}

.login-brand__title {
  font-family: var(--font-display);
  font-size: clamp(25px, 5vw, 30px);
  font-weight: 700;
  color: var(--color-ink);
  line-height: var(--leading-tight);
}

.login-brand__subtitle {
  margin-top: var(--space-3);
  color: var(--color-muted);
  font-size: var(--text-sm);
}

.login-form {
  display: grid;
  gap: var(--space-7);
}

.login-field {
  min-width: 0;
  display: grid;
  gap: var(--space-2);
}

.login-field > span:first-child {
  color: var(--color-ink-soft);
  font-size: var(--text-sm);
  font-weight: 600;
}

.login-input-frame {
  position: relative;
  display: block;
}

.login-input-frame :deep(input) {
  min-height: 46px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: color-mix(in oklch, var(--color-bg) 42%, var(--color-surface));
  color: var(--color-ink);
  font-size: var(--text-sm);
  transition:
    border-color var(--motion-fast) var(--ease-standard),
    box-shadow var(--motion-fast) var(--ease-standard),
    background-color var(--motion-fast) var(--ease-standard);
}

.login-input-frame :deep(input:focus) {
  border-color: var(--color-primary);
  box-shadow: var(--focus-ring);
}

.login-password-frame :deep(input) {
  padding-right: 52px;
}

.login-password-toggle {
  position: absolute;
  top: 1px;
  right: 1px;
  width: 44px;
  height: 44px;
  min-height: 44px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-muted);
  box-shadow: none;
}

.login-password-toggle:hover:not(:disabled) {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  transform: none;
}

.login-password-toggle svg,
.login-submit svg,
.login-security-note svg {
  display: block;
  width: 18px;
  height: 18px;
}

.login-options {
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-7);
  color: var(--color-muted);
  font-size: var(--text-sm);
}

.login-checkbox {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
}

.login-checkbox :deep(input[type="checkbox"]) {
  width: 14px;
  min-width: 14px;
  height: 14px;
  min-height: 0;
  margin: 0;
  padding: 0;
  accent-color: var(--color-accent);
}

.login-link {
  min-height: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--color-accent);
  box-shadow: none;
  font-size: var(--text-sm);
  font-weight: 650;
}

.login-link:hover:not(:disabled) {
  transform: none;
  box-shadow: none;
  color: var(--color-ink);
}

.login-submit {
  width: 100%;
  min-height: 48px;
  margin-top: 2px;
  border-radius: var(--radius-md);
  background: var(--color-accent);
  color: var(--color-accent-on);
  font-weight: 700;
  gap: var(--space-2);
  transition: all var(--motion-fast) var(--ease-standard);
}

.login-submit:hover:not(:disabled) {
  background: var(--color-accent-hover);
  transform: translateY(-1px);
  box-shadow: var(--elev-raised);
}

.login-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.login-security-note {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  margin-top: 22px;
  padding-top: var(--space-7);
  border-top: 1px solid var(--color-border);
  color: var(--color-muted);
  font-size: var(--text-xs);
  line-height: 1.65;
}

.login-security-note svg {
  flex: 0 0 auto;
  width: 14px;
  height: 14px;
  color: var(--color-primary);
}

.login-card__foot {
  margin-top: var(--space-5);
  text-align: center;
  color: var(--color-ink-soft);
  font-size: var(--text-sm);
}

.login-link--accent {
  color: var(--color-accent);
  font-weight: 700;
}

.login-footnote {
  margin-top: 20px;
  color: color-mix(in oklch, var(--color-muted) 82%, transparent);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.08em;
  text-align: center;
}

@keyframes login-enter {
  from {
    opacity: 0;
    transform: translateY(12px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 600px) {
  .login-shell {
    align-items: flex-start;
    padding-top: max(40px, 8vh);
  }

  .login-contour-one {
    top: -8%;
    right: -52%;
  }

  .login-contour-two {
    bottom: -10%;
    left: -60%;
  }

  .login-tree-one {
    top: 5%;
    left: 8%;
  }

  .login-tree-two {
    right: 8%;
    bottom: 5%;
  }

  .login-card {
    border-radius: var(--radius-lg);
  }
}

@media (max-width: 430px) {
  .login-shell {
    padding-inline: var(--space-5);
  }

  .login-options {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-3);
  }
}

@media (prefers-reduced-motion: reduce) {
  .login-card {
    animation: none;
  }
}
</style>
