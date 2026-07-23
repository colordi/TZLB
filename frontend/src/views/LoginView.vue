<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowRight, Eye, EyeOff, ShieldCheck, TreePine } from "@lucide/vue";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  <section
    class="relative flex min-h-svh items-center justify-center bg-background px-4 py-10"
    data-testid="login-page"
  >
    <div
      class="pointer-events-none absolute inset-0 overflow-hidden opacity-70"
      aria-hidden="true"
    >
      <div
        class="absolute -top-24 -right-16 size-[28rem] rounded-full bg-primary/10 blur-3xl"
      />
      <div
        class="absolute -bottom-28 -left-20 size-[32rem] rounded-full bg-muted blur-3xl"
      />
    </div>

    <Card class="relative z-10 w-full max-w-md border-border shadow-lg">
      <CardHeader class="items-center space-y-3 text-center">
        <div
          class="flex size-12 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm"
          aria-hidden="true"
        >
          <TreePine class="size-6" :stroke-width="2" />
        </div>
        <div class="space-y-1.5">
          <CardTitle class="text-2xl font-bold tracking-tight">
            林业调查工作台
          </CardTitle>
          <CardDescription>使用林业管理部门统一账号登录</CardDescription>
        </div>
      </CardHeader>

      <CardContent>
        <form class="grid gap-5" novalidate @submit.prevent="handleSubmit">
          <div class="grid gap-2">
            <Label for="login-username">账号</Label>
            <Input
              id="login-username"
              v-model.trim="username"
              :disabled="submitting"
              autocomplete="username"
              name="username"
              placeholder="请输入账号"
              required
              type="text"
            />
          </div>

          <div class="grid gap-2">
            <Label for="login-password">密码</Label>
            <div class="relative">
              <Input
                id="login-password"
                v-model.trim="password"
                class="pr-11"
                :disabled="submitting"
                autocomplete="current-password"
                name="password"
                placeholder="请输入密码"
                required
                :type="showPassword ? 'text' : 'password'"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                class="absolute top-1/2 right-1 -translate-y-1/2 text-muted-foreground"
                data-testid="login-password-toggle"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                :aria-pressed="showPassword ? 'true' : 'false'"
                :disabled="submitting"
                @click="showPassword = !showPassword"
              >
                <EyeOff v-if="showPassword" class="size-4" />
                <Eye v-else class="size-4" />
              </Button>
            </div>
          </div>

          <div class="flex flex-wrap items-center justify-between gap-3">
            <label class="flex items-center gap-2 text-sm text-muted-foreground">
              <Checkbox
                id="remember-me"
                v-model="rememberMe"
                :disabled="submitting"
              />
              <span>记住我</span>
            </label>

            <Button
              type="button"
              variant="link"
              class="h-auto px-0 text-sm"
              :disabled="submitting"
              @click="handleForgotPassword"
            >
              忘记密码？
            </Button>
          </div>

          <Button type="submit" class="w-full" :disabled="submitting">
            <span>{{ submitting ? "正在进入" : "进入工作台" }}</span>
            <ArrowRight class="size-4" />
          </Button>
        </form>

        <div
          class="mt-6 flex items-start gap-2 border-t border-border pt-4 text-xs leading-relaxed text-muted-foreground"
        >
          <ShieldCheck class="mt-0.5 size-3.5 shrink-0 text-primary" />
          <span>系统将记录登录时间、设备与关键操作，用于安全审计和数据追溯。</span>
        </div>
      </CardContent>

      <CardFooter class="flex flex-col gap-3 text-center text-sm text-muted-foreground">
        <p>
          还没有账号？
          <Button
            type="button"
            variant="link"
            class="h-auto px-1 font-semibold"
            :disabled="submitting"
            @click="handleRequestAccess"
          >
            申请加入
          </Button>
        </p>
        <p class="font-mono text-[10px] tracking-wide text-muted-foreground/80">
          北京市林业资源调查与监测
        </p>
      </CardFooter>
    </Card>
  </section>
</template>
