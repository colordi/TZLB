<script setup>
import { computed, onMounted, ref } from "vue";
import {
  RefreshCw,
  Plus,
  Pencil,
  Trash2,
  KeyRound,
  UserCheck,
  UserX,
  ShieldCheck,
  Shield,
} from "@lucide/vue";

import {
  fetchUsers,
  createUser,
  updateUser,
  deleteUser,
  resetUserPassword,
} from "../api/admin.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const { error, info } = useToast();
const loading = ref(false);
const users = ref([]);

const showCreate = ref(false);
const showEdit = ref(false);
const showResetPwd = ref(false);
const editingUser = ref(null);
const resettingUserId = ref(null);

const form = ref({
  username: "",
  password: "",
  display_name: "",
  role: "investigator",
});
const editForm = ref({
  display_name: "",
  role: "investigator",
  is_active: true,
});
const resetPwdForm = ref({
  new_password: "",
});
const saving = ref(false);

const roleLabel = {
  admin: "管理员",
  investigator: "调查员",
};

const activeUsers = computed(() => users.value.filter((u) => u.is_active));

async function load() {
  if (loading.value) return;
  loading.value = true;
  try {
    users.value = await fetchUsers();
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`加载用户列表失败：${err.message || err}`, "加载失败");
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  form.value = { username: "", password: "", display_name: "", role: "investigator" };
  showCreate.value = true;
}

async function handleCreate() {
  saving.value = true;
  try {
    await createUser({ ...form.value });
    info(`用户 ${form.value.username} 创建成功`, "创建成功");
    showCreate.value = false;
    await load();
  } catch (err) {
    error(`创建用户失败：${err.message || err}`, "创建失败");
  } finally {
    saving.value = false;
  }
}

function openEdit(user) {
  editingUser.value = user;
  editForm.value = {
    display_name: user.display_name || "",
    role: user.role,
    is_active: user.is_active,
  };
  showEdit.value = true;
}

async function handleEdit() {
  if (!editingUser.value) return;
  saving.value = true;
  try {
    const payload = {};
    if (editForm.value.display_name !== editingUser.value.display_name) {
      payload.display_name = editForm.value.display_name;
    }
    if (editForm.value.role !== editingUser.value.role) {
      payload.role = editForm.value.role;
    }
    if (editForm.value.is_active !== editingUser.value.is_active) {
      payload.is_active = editForm.value.is_active;
    }
    if (Object.keys(payload).length === 0) {
      showEdit.value = false;
      return;
    }
    await updateUser(editingUser.value.id, payload);
    info("用户信息已更新", "更新成功");
    showEdit.value = false;
    await load();
  } catch (err) {
    error(`更新用户失败：${err.message || err}`, "更新失败");
  } finally {
    saving.value = false;
  }
}

function openResetPwd(user) {
  resettingUserId.value = user.id;
  resetPwdForm.value = { new_password: "" };
  showResetPwd.value = true;
}

async function handleResetPwd() {
  if (!resettingUserId.value) return;
  saving.value = true;
  try {
    await resetUserPassword(resettingUserId.value, resetPwdForm.value.new_password);
    info("密码已重置", "重置成功");
    showResetPwd.value = false;
  } catch (err) {
    error(`重置密码失败：${err.message || err}`, "重置失败");
  } finally {
    saving.value = false;
  }
}

async function handleDelete(user) {
  if (!confirm(`确认删除用户「${user.display_name || user.username}」？此操作不可撤销。`)) {
    return;
  }
  try {
    await deleteUser(user.id);
    info(`用户 ${user.username} 已删除`, "删除成功");
    await load();
  } catch (err) {
    error(`删除用户失败：${err.message || err}`, "删除失败");
  }
}

onMounted(() => {
  load();
});
</script>

<template>
  <div class="mx-auto w-full max-w-6xl space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="space-y-1">
        <h1 class="text-2xl font-bold tracking-tight">用户管理</h1>
        <p class="text-sm text-muted-foreground">
          管理系统账号，共 {{ users.length }} 人（活跃 {{ activeUsers.length }} 人）
        </p>
      </div>
      <div class="page-actions flex items-center gap-2">
        <Button type="button" variant="outline" size="sm" :disabled="loading" @click="load">
          <RefreshCw class="size-4" :class="{ 'animate-spin': loading }" />
          <span>刷新</span>
        </Button>
        <Button type="button" size="sm" @click="openCreate">
          <Plus class="size-4" />
          <span>新建用户</span>
        </Button>
      </div>
    </div>

    <div class="overflow-x-auto rounded-md border">
      <Table class="data-table min-w-[48rem]">
        <TableHeader>
          <TableRow>
            <TableHead>用户名</TableHead>
            <TableHead>显示名称</TableHead>
            <TableHead>角色</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>最后登录</TableHead>
            <TableHead>创建时间</TableHead>
            <TableHead class="text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-for="user in users" :key="user.id">
            <TableCell><code class="text-xs">{{ user.username }}</code></TableCell>
            <TableCell>{{ user.display_name }}</TableCell>
            <TableCell>
              <Badge :variant="user.role === 'admin' ? 'default' : 'secondary'">
                <ShieldCheck v-if="user.role === 'admin'" class="size-3.5" />
                <Shield v-else class="size-3.5" />
                {{ roleLabel[user.role] || user.role }}
              </Badge>
            </TableCell>
            <TableCell>
              <span class="inline-flex items-center gap-1.5 text-sm">
                <span
                  class="size-2 rounded-full"
                  :class="user.is_active ? 'bg-emerald-500' : 'bg-muted-foreground/40'"
                />
                {{ user.is_active ? "活跃" : "停用" }}
              </span>
            </TableCell>
            <TableCell class="text-muted-foreground">
              {{ user.last_login_at ? new Date(user.last_login_at).toLocaleString("zh-CN") : "--" }}
            </TableCell>
            <TableCell class="text-muted-foreground">
              {{ user.created_at ? new Date(user.created_at).toLocaleDateString("zh-CN") : "--" }}
            </TableCell>
            <TableCell class="text-right">
              <div class="inline-flex items-center gap-1">
                <Button type="button" variant="ghost" size="icon" title="编辑" @click="openEdit(user)">
                  <Pencil class="size-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  title="重置密码"
                  @click="openResetPwd(user)"
                >
                  <KeyRound class="size-4" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  class="text-destructive hover:text-destructive"
                  title="删除"
                  @click="handleDelete(user)"
                >
                  <Trash2 class="size-4" />
                </Button>
              </div>
            </TableCell>
          </TableRow>
          <TableRow v-if="users.length === 0 && !loading">
            <TableCell colspan="7" class="h-24 text-center text-muted-foreground">
              暂无用户数据
            </TableCell>
          </TableRow>
          <TableRow v-if="loading">
            <TableCell colspan="7" class="h-24 text-center text-muted-foreground">
              加载中…
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
  </div>

  <Dialog v-model:open="showCreate">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>新建用户</DialogTitle>
      </DialogHeader>
      <form class="grid gap-4" @submit.prevent="handleCreate">
        <div class="grid gap-2">
          <Label for="create-username">用户名</Label>
          <Input id="create-username" v-model="form.username" required placeholder="登录账号" />
        </div>
        <div class="grid gap-2">
          <Label for="create-display">显示名称</Label>
          <Input id="create-display" v-model="form.display_name" placeholder="用户显示名称（选填）" />
        </div>
        <div class="grid gap-2">
          <Label for="create-password">密码</Label>
          <Input
            id="create-password"
            v-model="form.password"
            type="password"
            required
            minlength="6"
            placeholder="至少 6 位"
          />
        </div>
        <div class="grid gap-2">
          <Label for="create-role">角色</Label>
          <select
            id="create-role"
            v-model="form.role"
            class="h-9 rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value="investigator">调查员</option>
            <option value="admin">管理员</option>
          </select>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" @click="showCreate = false">取消</Button>
          <Button type="submit" :disabled="saving">{{ saving ? "创建中…" : "创建" }}</Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>

  <Dialog v-model:open="showEdit">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>编辑用户</DialogTitle>
        <p class="text-sm text-muted-foreground">{{ editingUser?.username }}</p>
      </DialogHeader>
      <form class="grid gap-4" @submit.prevent="handleEdit">
        <div class="grid gap-2">
          <Label for="edit-display">显示名称</Label>
          <Input id="edit-display" v-model="editForm.display_name" placeholder="用户显示名称" />
        </div>
        <div class="grid gap-2">
          <Label for="edit-role">角色</Label>
          <select
            id="edit-role"
            v-model="editForm.role"
            class="h-9 rounded-md border border-input bg-background px-3 text-sm"
          >
            <option value="investigator">调查员</option>
            <option value="admin">管理员</option>
          </select>
        </div>
        <label class="flex items-center gap-2 text-sm">
          <Checkbox v-model="editForm.is_active" />
          <UserCheck v-if="editForm.is_active" class="size-4" />
          <UserX v-else class="size-4" />
          <span>{{ editForm.is_active ? "活跃" : "停用" }}</span>
        </label>
        <DialogFooter>
          <Button type="button" variant="outline" @click="showEdit = false">取消</Button>
          <Button type="submit" :disabled="saving">{{ saving ? "保存中…" : "保存" }}</Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>

  <Dialog v-model:open="showResetPwd">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>重置密码</DialogTitle>
      </DialogHeader>
      <form class="grid gap-4" @submit.prevent="handleResetPwd">
        <div class="grid gap-2">
          <Label for="reset-password">新密码</Label>
          <Input
            id="reset-password"
            v-model="resetPwdForm.new_password"
            type="password"
            required
            minlength="6"
            placeholder="至少 6 位"
          />
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" @click="showResetPwd = false">取消</Button>
          <Button type="submit" :disabled="saving">{{ saving ? "重置中…" : "确认重置" }}</Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>
