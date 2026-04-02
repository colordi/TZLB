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
    <div class="login-scene" aria-hidden="true">
      <div class="login-scene__image"></div>
      <div class="login-scene__shade"></div>
      <div class="login-scene__mesh"></div>
    </div>

    <main class="login-content">
      <div class="login-card">
        <div class="login-brand">
          <div class="login-brand__mark" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path
                d="M12 3.25 7.75 9h1.7l-2.85 4h2.14l-1.64 4.75h9.8L15.27 13h2.14l-2.85-4h1.69L12 3.25Zm0 2.62 1.7 2.28h-1.15l2.84 4h-1.9l1.16 3.35h-5.3l1.16-3.35H8.61l2.84-4h-1.15L12 5.87Z"
              />
            </svg>
          </div>
          <p class="login-brand__eyebrow">Forestry Survey Workbench</p>
          <h1>林业调查工作台</h1>
          <p class="login-brand__summary">
            面向林业调查、点位核查与工单录入的一体化工作入口。
          </p>
        </div>

        <form class="login-form" @submit.prevent="handleSubmit">
          <div class="login-field">
            <label for="login-username">用户名</label>
            <div class="login-input-shell">
              <span class="login-input-shell__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path
                    d="M12 4.25a4 4 0 1 1 0 8 4 4 0 0 1 0-8Zm0 1.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5Zm0 7.75c4.05 0 7.35 2.17 7.35 4.85a.75.75 0 0 1-1.5 0c0-1.58-2.35-3.35-5.85-3.35s-5.85 1.77-5.85 3.35a.75.75 0 0 1-1.5 0c0-2.68 3.3-4.85 7.35-4.85Z"
                  />
                </svg>
              </span>
              <input
                id="login-username"
                v-model.trim="username"
                :disabled="submitting"
                autocomplete="username"
                name="username"
                placeholder="输入您的用户名"
                type="text"
              />
            </div>
          </div>

          <div class="login-field">
            <label for="login-password">密码</label>
            <div class="login-input-shell">
              <span class="login-input-shell__icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path
                    d="M12 2.75A4.25 4.25 0 0 0 7.75 7v2H7A2.75 2.75 0 0 0 4.25 11.75v6.5A2.75 2.75 0 0 0 7 21h10a2.75 2.75 0 0 0 2.75-2.75v-6.5A2.75 2.75 0 0 0 17 9h-.75V7A4.25 4.25 0 0 0 12 2.75Zm2.75 6.25h-5.5V7a2.75 2.75 0 1 1 5.5 0v2Zm-7.5 1.5h10c.69 0 1.25.56 1.25 1.25v6.5c0 .69-.56 1.25-1.25 1.25H7c-.69 0-1.25-.56-1.25-1.25v-6.5c0-.69.56-1.25 1.25-1.25Zm5 2.25a.75.75 0 0 0-1.5 0v2.5a.75.75 0 0 0 1.5 0v-2.5Z"
                  />
                </svg>
              </span>
              <input
                id="login-password"
                v-model.trim="password"
                :disabled="submitting"
                autocomplete="current-password"
                name="password"
                placeholder="••••••••"
                type="password"
              />
            </div>
          </div>

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
            <span>{{ submitting ? "正在登录" : "立即登录" }}</span>
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M12.97 5.97a.75.75 0 0 1 1.06 0l5.5 5.5a.75.75 0 0 1 0 1.06l-5.5 5.5a.75.75 0 1 1-1.06-1.06l4.22-4.22H5a.75.75 0 0 1 0-1.5h12.19l-4.22-4.22a.75.75 0 0 1 0-1.06Z"
              />
            </svg>
          </button>
        </form>

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
      </div>
    </main>

  </section>
</template>

<style scoped>
@import url("https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap");

.login-page {
  --login-card-bg: rgba(255, 255, 255, 0.82);
  --login-card-line: rgba(222, 230, 220, 0.65);
  --login-ink: #18261c;
  --login-ink-soft: #57675d;
  --login-primary: #0b6137;
  --login-primary-soft: #a9efbf;
  --login-primary-strong: #1e7c49;
  --login-shadow: 0 28px 70px rgba(22, 39, 25, 0.16);

  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: var(--login-ink);
  font-family:
    "Manrope",
    "PingFang SC",
    "Hiragino Sans GB",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    sans-serif;
}

.login-scene,
.login-scene__image,
.login-scene__shade,
.login-scene__mesh {
  position: absolute;
  inset: 0;
}

.login-scene {
  z-index: 0;
}

.login-scene__image {
  background:
    linear-gradient(135deg, rgba(13, 41, 20, 0.18), rgba(13, 41, 20, 0.02)),
    url("https://lh3.googleusercontent.com/aida-public/AB6AXuBNjSdqBxSstWIlUnscc6lPiLbw2LrGlzMMBvlTjuUOTbpdncyrcFRIM2R1YYhZoIJAYKOFdY7gZgtC9bp4b5jR_ARmwQoPlGHgiqmI6KNKIUudy2ITqx2-jV1OHxHL2m23FrQmXnR1vQxgbhHJ9OdMsG9dCcHmvcje32F6tRWpUhcyIBbCN_gI0wnCXZ28al5wnoDpmNFb9At2-1DDlyP6t2w_w5ZFXGzYfW_pvLScQ6JyvgIezXX3CYl1e046ZY5iiHfOtupvKUE")
      center / cover;
  filter: blur(8px);
  transform: scale(1.06);
}

.login-scene__shade {
  background:
    radial-gradient(circle at 18% 20%, rgba(186, 241, 199, 0.36), transparent 26%),
    radial-gradient(circle at 83% 16%, rgba(255, 255, 255, 0.36), transparent 24%),
    linear-gradient(180deg, rgba(247, 250, 244, 0.3), rgba(247, 250, 244, 0.76));
}

.login-scene__mesh {
  opacity: 0.45;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.2) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.2) 1px, transparent 1px);
  background-size: 4.5rem 4.5rem;
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.5), transparent 78%);
}

.login-content {
  position: relative;
  z-index: 1;
}

.login-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1.25rem;
}

.login-card {
  width: min(100%, 30rem);
  padding: 2.2rem;
  border: 1px solid var(--login-card-line);
  border-radius: 1.5rem;
  background: var(--login-card-bg);
  box-shadow: var(--login-shadow);
  backdrop-filter: blur(24px);
}

.login-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: 2rem;
}

.login-brand__mark {
  width: 4.25rem;
  height: 4.25rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: linear-gradient(145deg, #2d7a4d, #a8efbd);
  color: #fff;
  box-shadow: 0 16px 28px rgba(18, 52, 29, 0.18);
}

.login-brand__mark svg {
  width: 2rem;
  height: 2rem;
  fill: currentColor;
}

.login-brand__eyebrow {
  margin-top: 1.15rem;
  color: var(--login-primary);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.login-brand h1 {
  margin-top: 0.45rem;
  font-size: clamp(2rem, 5vw, 2.5rem);
  line-height: 1.02;
  letter-spacing: -0.06em;
  color: var(--login-primary);
}

.login-brand__summary {
  margin-top: 0.85rem;
  max-width: 22rem;
  color: var(--login-ink-soft);
  font-size: 0.96rem;
  line-height: 1.65;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
}

.login-field {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.login-field label {
  padding-left: 0.3rem;
  color: var(--login-ink-soft);
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.login-input-shell {
  position: relative;
}

.login-input-shell__icon {
  position: absolute;
  top: 50%;
  left: 1rem;
  width: 1.15rem;
  height: 1.15rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--login-primary);
  transform: translateY(-50%);
}

.login-input-shell__icon svg {
  width: 1.15rem;
  height: 1.15rem;
  fill: currentColor;
}

.login-input-shell :deep(input) {
  padding-left: 3rem;
  min-height: 3.55rem;
  border-radius: 1rem;
  border-color: rgba(179, 198, 182, 0.45);
  background: rgba(255, 255, 255, 0.94);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.55);
}

.login-input-shell :deep(input:focus) {
  border-color: rgba(11, 97, 55, 0.28);
}

.login-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  font-size: 0.92rem;
}

.login-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  color: var(--login-ink-soft);
  cursor: pointer;
}

.login-checkbox :deep(input) {
  width: 1rem;
  min-height: 1rem;
  height: 1rem;
  margin: 0;
  accent-color: var(--login-primary);
}

.login-submit {
  min-height: 3.6rem;
  margin-top: 0.25rem;
  border-radius: 1rem;
  background: linear-gradient(135deg, var(--login-primary), var(--login-primary-strong));
  box-shadow: 0 22px 34px rgba(10, 97, 54, 0.22);
}

.login-submit svg {
  width: 1.1rem;
  height: 1.1rem;
  fill: currentColor;
}

.login-link {
  min-height: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--login-primary);
  box-shadow: none;
  font-size: 0.92rem;
  font-weight: 700;
}

.login-link:hover {
  transform: none;
  box-shadow: none;
  color: var(--login-primary-strong);
}

.login-link--accent {
  color: #256f44;
}

.login-card__foot {
  margin-top: 1.8rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(179, 198, 182, 0.28);
  text-align: center;
  color: var(--login-ink-soft);
  font-size: 0.94rem;
}

@media (max-width: 720px) {
  .login-content {
    padding: 1rem;
  }

  .login-card {
    padding: 1.45rem;
    border-radius: 1.25rem;
  }

  .login-brand__mark {
    width: 3.75rem;
    height: 3.75rem;
  }

  .login-options {
    flex-direction: column;
    align-items: stretch;
  }

  .login-options {
    gap: 0.85rem;
  }
}
</style>
