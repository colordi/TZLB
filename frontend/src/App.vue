<script setup>
import { computed, ref } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { LogOut, Menu, TreePine } from "@lucide/vue";

import {
  getDefaultRouteForUser,
  userHasAnyRole,
} from "./auth/permissions.js";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import ToastViewport from "./components/ui/ToastViewport.vue";
import { useAuthSession } from "./composables/useAuthSession.js";
import { useToast } from "./composables/useToast.js";
import { NAV_GROUPS } from "./config/navigation.js";
import { cn } from "@/lib/utils";

const route = useRoute();
const router = useRouter();
const hideShell = computed(() => Boolean(route.meta?.hideShell));
const useFullBleedMain = computed(() => Boolean(route.meta?.fullBleed));
const loggingOut = ref(false);
const { user, signOut } = useAuthSession();
const { error, info } = useToast();

const currentUserName = computed(
  () => user.value?.display_name || user.value?.username || "",
);
const homePath = computed(() =>
  user.value ? getDefaultRouteForUser(user.value) : "/workorder",
);

const visibleNavGroups = computed(() =>
  NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter(
      (item) => !user.value || userHasAnyRole(user.value, item.requiredRoles),
    ),
  })).filter((group) => group.items.length > 0),
);

const pageTitle = computed(() => route.meta?.section || "工作界面");

function isActivePath(to) {
  if (to === "/admin") {
    return route.path === "/admin";
  }
  return route.path === to || route.path.startsWith(`${to}/`);
}

async function handleLogout() {
  if (loggingOut.value) {
    return;
  }

  loggingOut.value = true;
  try {
    await signOut();
    info("您已安全退出当前账号。", "退出成功");
    await router.push("/login");
  } catch (logoutError) {
    error(`${logoutError.message || logoutError}`, "退出失败");
  } finally {
    loggingOut.value = false;
  }
}

/** 仅在 SidebarProvider 内使用 */
const MobileMenuTrigger = {
  name: "MobileMenuTrigger",
  components: { Button, Menu },
  setup() {
    const { setOpenMobile } = useSidebar();
    return { setOpenMobile };
  },
  template: `
    <Button
      type="button"
      variant="outline"
      size="icon"
      class="size-8 md:hidden"
      data-testid="mobile-menu-trigger"
      aria-label="打开导航菜单"
      @click="setOpenMobile(true)"
    >
      <Menu class="size-4" />
      <span class="sr-only">打开菜单</span>
    </Button>
  `,
};

const DesktopSidebarToggle = {
  name: "DesktopSidebarToggle",
  components: { SidebarTrigger },
  setup() {
    const { state } = useSidebar();
    return { state };
  },
  template: `
    <SidebarTrigger
      class="sidebar-toggle-btn hidden size-7 md:inline-flex"
      :aria-label="state === 'collapsed' ? '展开侧边栏' : '收起侧边栏'"
    />
  `,
};
</script>

<template>
  <div class="app-shell min-h-svh bg-background text-foreground">
    <template v-if="hideShell">
      <main class="site-main is-standalone min-h-svh">
        <RouterView />
      </main>
      <ToastViewport />
    </template>

    <SidebarProvider v-else :default-open="true" class="min-h-svh">
      <Sidebar collapsible="icon" class="app-sidebar border-sidebar-border">
        <SidebarHeader class="app-sidebar-brand-row gap-1 border-b border-sidebar-border p-2">
          <RouterLink
            :to="homePath"
            class="app-sidebar-brand flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-1.5 text-sidebar-foreground outline-none hover:bg-sidebar-accent"
          >
            <span
              class="flex size-8 shrink-0 items-center justify-center rounded-md bg-sidebar-primary text-sidebar-primary-foreground"
              aria-hidden="true"
            >
              <TreePine class="size-4" :stroke-width="2" />
            </span>
            <span class="min-w-0 group-data-[collapsible=icon]:hidden">
              <strong class="block truncate text-sm font-semibold leading-tight">
                林业调查工作台
              </strong>
              <span class="block truncate text-[10px] tracking-wide text-sidebar-foreground/60">
                FORESTRY SURVEY
              </span>
            </span>
          </RouterLink>
          <DesktopSidebarToggle />
        </SidebarHeader>

        <SidebarContent>
          <template v-for="group in visibleNavGroups" :key="group.label">
            <SidebarGroup>
              <SidebarGroupLabel class="app-sidebar-caption">
                {{ group.label }}
              </SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu class="app-sidebar-nav">
                  <SidebarMenuItem v-for="item in group.items" :key="item.to">
                    <SidebarMenuButton
                      as-child
                      :is-active="isActivePath(item.to)"
                      :tooltip="item.label"
                    >
                      <RouterLink
                        :to="item.to"
                        class="app-sidebar-link"
                        :class="{ 'router-link-active': isActivePath(item.to) }"
                        :data-testid="`sidebar-link-${item.testId}`"
                      >
                        <component :is="item.icon" />
                        <span>{{ item.label }}</span>
                      </RouterLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </template>
        </SidebarContent>

        <SidebarFooter class="border-t border-sidebar-border">
          <div class="app-sidebar-profile flex items-center gap-2 px-2 py-1.5 text-sidebar-foreground">
            <span
              class="flex size-7 shrink-0 items-center justify-center rounded-full bg-sidebar-accent text-xs font-bold"
              aria-hidden="true"
            >
              {{ (currentUserName || "账").slice(0, 1) }}
            </span>
            <span class="min-w-0 group-data-[collapsible=icon]:hidden">
              <strong class="block truncate text-sm">{{ currentUserName || "账号" }}</strong>
              <span class="block text-[10px] text-sidebar-foreground/60">当前登录用户</span>
            </span>
          </div>
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>

      <SidebarInset class="min-w-0">
        <header
          class="site-header sticky top-0 z-20 flex h-14 shrink-0 items-center border-b border-border bg-background/95 px-3 backdrop-blur md:px-4"
        >
          <div class="site-header-shell flex w-full min-w-0 items-center gap-3">
            <MobileMenuTrigger />

            <RouterLink
              :to="homePath"
              class="site-brand flex min-w-0 items-center gap-2 md:hidden"
            >
              <span
                class="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground"
              >
                <TreePine class="size-4" />
              </span>
              <span class="truncate text-sm font-semibold">林业调查工作台</span>
            </RouterLink>

            <div class="site-section-title hidden min-w-0 flex-1 md:block">
              <div class="flex min-w-0 items-center gap-2 text-sm text-muted-foreground">
                <span>工作台</span>
                <span class="text-border">/</span>
                <strong class="truncate font-semibold text-foreground">{{ pageTitle }}</strong>
              </div>
            </div>

            <div class="site-actions ml-auto flex items-center gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger as-child>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    class="user-pill user-dropdown-wrap max-w-[10rem]"
                  >
                    <span class="truncate">{{ currentUserName || "账号" }}</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" class="user-dropdown w-40">
                  <DropdownMenuItem
                    class="cursor-pointer gap-2"
                    :disabled="loggingOut"
                    @click="handleLogout"
                  >
                    <LogOut class="size-4" />
                    <span>{{ loggingOut ? "退出中" : "退出登录" }}</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>

        <main
          class="site-main flex min-h-0 flex-1 flex-col"
          :class="cn(useFullBleedMain ? 'is-full-bleed overflow-hidden p-0' : 'overflow-auto p-4 md:p-6')"
        >
          <RouterView />
        </main>
      </SidebarInset>
      <ToastViewport />
    </SidebarProvider>
  </div>
</template>
