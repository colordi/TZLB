<script setup>
import { computed, onMounted, ref } from "vue";
import { RefreshCw, Plus, Pencil, Trash2, KeyRound, UserCheck, UserX, ShieldCheck, Shield } from "@lucide/vue";

import {
  fetchUsers,
  createUser,
  updateUser,
  deleteUser,
  resetUserPassword,
} from "../api/admin.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";

const { error, info } = useToast();
const loading = ref(false);
const users = ref([]);

/* ── Dialogs ── */
const showCreate = ref(false);
const showEdit = ref(false);
const showResetPwd = ref(false);
const editingUser = ref(null);
const resettingUserId = ref(null);

/* ── Form state ── */
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

/* ── Locale map for role ── */
const roleLabel = {
  admin: "管理员",
  investigator: "调查员",
};

const activeUsers = computed(() => users.value.filter((u) => u.is_active));
const inactiveUsers = computed(() => users.value.filter((u) => !u.is_active));

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
  <div class="admin-page">
    <div class="page-header">
      <div class="page-header-copy">
        <h1 class="page-title">用户管理</h1>
        <p class="page-desc">管理系统账号，共 {{ users.length }} 人（活跃 {{ activeUsers.length }} 人）</p>
      </div>
      <div class="page-actions">
        <button type="button" class="btn btn-secondary" :disabled="loading" @click="load">
          <RefreshCw :size="16" :stroke-width="2" :class="{ 'is-spinning': loading }" />
          <span>刷新</span>
        </button>
        <button type="button" class="btn btn-primary" @click="openCreate">
          <Plus :size="16" :stroke-width="2" />
          <span>新建用户</span>
        </button>
      </div>
    </div>

    <!-- User table -->
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>用户名</th>
            <th>显示名称</th>
            <th>角色</th>
            <th>状态</th>
            <th>最后登录</th>
            <th>创建时间</th>
            <th class="cell-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td><code>{{ user.username }}</code></td>
            <td>{{ user.display_name }}</td>
            <td>
              <span class="badge" :class="user.role === 'admin' ? 'badge-admin' : 'badge-investigator'">
                <ShieldCheck v-if="user.role === 'admin'" :size="14" :stroke-width="2" />
                <Shield v-else :size="14" :stroke-width="2" />
                {{ roleLabel[user.role] || user.role }}
              </span>
            </td>
            <td>
              <span class="status-dot" :class="user.is_active ? 'status-active' : 'status-inactive'"></span>
              {{ user.is_active ? "活跃" : "停用" }}
            </td>
            <td class="cell-muted">{{ user.last_login_at ? new Date(user.last_login_at).toLocaleString("zh-CN") : "--" }}</td>
            <td class="cell-muted">{{ user.created_at ? new Date(user.created_at).toLocaleDateString("zh-CN") : "--" }}</td>
            <td class="cell-actions">
              <div class="action-btns">
                <button type="button" class="icon-btn" title="编辑" @click="openEdit(user)">
                  <Pencil :size="15" :stroke-width="2" />
                </button>
                <button type="button" class="icon-btn" title="重置密码" @click="openResetPwd(user)">
                  <KeyRound :size="15" :stroke-width="2" />
                </button>
                <button type="button" class="icon-btn icon-btn-danger" title="删除" @click="handleDelete(user)">
                  <Trash2 :size="15" :stroke-width="2" />
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="users.length === 0 && !loading">
            <td colspan="7" class="cell-empty">暂无用户数据</td>
          </tr>
          <tr v-if="loading">
            <td colspan="7" class="cell-empty">加载中…</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- Create Modal -->
  <Teleport to="body">
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
      <div class="modal">
        <div class="modal-head">
          <h3>新建用户</h3>
        </div>
        <form class="modal-body" @submit.prevent="handleCreate">
          <label class="field">
            <span>用户名</span>
            <input v-model="form.username" type="text" required placeholder="登录账号" />
          </label>
          <label class="field">
            <span>显示名称</span>
            <input v-model="form.display_name" type="text" placeholder="用户显示名称（选填）" />
          </label>
          <label class="field">
            <span>密码</span>
            <input v-model="form.password" type="password" required minlength="6" placeholder="至少 6 位" />
          </label>
          <label class="field">
            <span>角色</span>
            <select v-model="form.role">
              <option value="investigator">调查员</option>
              <option value="admin">管理员</option>
            </select>
          </label>
          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="showCreate = false">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              {{ saving ? "创建中…" : "创建" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>

  <!-- Edit Modal -->
  <Teleport to="body">
    <div v-if="showEdit" class="modal-overlay" @click.self="showEdit = false">
      <div class="modal">
        <div class="modal-head">
          <h3>编辑用户</h3>
          <span class="modal-sub">{{ editingUser?.username }}</span>
        </div>
        <form class="modal-body" @submit.prevent="handleEdit">
          <label class="field">
            <span>显示名称</span>
            <input v-model="editForm.display_name" type="text" placeholder="用户显示名称" />
          </label>
          <label class="field">
            <span>角色</span>
            <select v-model="editForm.role">
              <option value="investigator">调查员</option>
              <option value="admin">管理员</option>
            </select>
          </label>
          <label class="field field-row">
            <span>启用状态</span>
            <label class="toggle">
              <input v-model="editForm.is_active" type="checkbox" />
              <span class="toggle-track">
                <UserCheck v-if="editForm.is_active" :size="14" :stroke-width="2" />
                <UserX v-else :size="14" :stroke-width="2" />
              </span>
              <span>{{ editForm.is_active ? "活跃" : "停用" }}</span>
            </label>
          </label>
          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="showEdit = false">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              {{ saving ? "保存中…" : "保存" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>

  <!-- Reset Password Modal -->
  <Teleport to="body">
    <div v-if="showResetPwd" class="modal-overlay" @click.self="showResetPwd = false">
      <div class="modal">
        <div class="modal-head">
          <h3>重置密码</h3>
        </div>
        <form class="modal-body" @submit.prevent="handleResetPwd">
          <label class="field">
            <span>新密码</span>
            <input v-model="resetPwdForm.new_password" type="password" required minlength="6" placeholder="至少 6 位" />
          </label>
          <div class="modal-actions">
            <button type="button" class="btn btn-secondary" @click="showResetPwd = false">取消</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              {{ saving ? "重置中…" : "确认重置" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.admin-page {
  max-width: var(--content-width, 1200px);
  width: 100%;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-6, 1.5rem);
  margin-bottom: var(--space-6, 1.5rem);
}

.page-header-copy {
  min-width: 0;
}

.page-title {
  margin: 0;
  font-family: var(--font-display);
  font-size: var(--text-2xl, 1.5rem);
  font-weight: 700;
  color: var(--color-text);
}

.page-desc {
  margin: var(--space-1, 0.25rem) 0 0;
  font-size: var(--text-sm, 0.875rem);
  color: var(--color-text-muted, #666);
}

.page-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3, 0.75rem);
  flex-shrink: 0;
}

/* table */
.table-wrap {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg, 12px);
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 0.7rem 1rem;
  text-align: left;
  font-size: var(--text-sm, 0.875rem);
}

.data-table th {
  background: var(--color-surface-container, #f5f5f5);
  font-weight: 600;
  color: var(--color-text-muted, #666);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.data-table td {
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
}

.data-table tr:last-child td {
  border-bottom: none;
}

.cell-actions {
  width: 120px;
  text-align: right;
}

.cell-muted {
  color: var(--color-text-muted, #666);
}

.cell-empty {
  text-align: center;
  padding: 2rem !important;
  color: var(--color-text-muted, #666);
}

.action-btns {
  display: inline-flex;
  gap: 0.25rem;
}

.icon-btn {
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: var(--radius-sm, 6px);
  background: transparent;
  color: var(--color-text-muted, #666);
  cursor: pointer;
  transition: all var(--motion-fast, 150ms) ease;
}

.icon-btn:hover {
  background: var(--color-surface-container, #eee);
  color: var(--color-text);
}

.icon-btn-danger:hover {
  background: #fee2e2;
  color: #dc2626;
}

/* badge */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-pill, 999px);
  font-size: var(--text-xs, 0.75rem);
  font-weight: 600;
  white-space: nowrap;
}

.badge-admin {
  background: #dbeafe;
  color: #1d4ed8;
}

.badge-investigator {
  background: #dcfce7;
  color: #16a34a;
}

/* status dot */
.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  margin-right: 6px;
  vertical-align: middle;
}

.status-active {
  background: #16a34a;
}

.status-inactive {
  background: #d1d5db;
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2, 0.5rem);
  min-height: 2.5rem;
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--motion-fast, 150ms) var(--ease-standard, ease);
  white-space: nowrap;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--color-surface);
  color: var(--color-text);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-surface-container, #f0f0f0);
}

.btn-primary {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.is-spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 5000;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.4);
  padding: 1rem;
}

.modal {
  width: 100%;
  max-width: 440px;
  background: var(--color-surface);
  border-radius: var(--radius-lg, 12px);
  border: 1px solid var(--color-border);
  box-shadow: var(--elev-raised, 0 4px 24px rgba(0,0,0,0.12));
}

.modal-head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 1.5rem 0;
}

.modal-head h3 {
  margin: 0;
  font-size: var(--text-lg, 1.125rem);
  font-weight: 700;
  color: var(--color-text);
}

.modal-sub {
  color: var(--color-text-muted, #666);
  font-size: var(--text-sm, 0.875rem);
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem 1.5rem 1.5rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.field > span {
  font-size: var(--text-sm, 0.875rem);
  font-weight: 600;
  color: var(--color-text);
}

.field input,
.field select {
  width: 100%;
  box-sizing: border-box;
  padding: 0.55rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm, 6px);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--text-sm, 0.875rem);
}

.field input:focus,
.field select:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px color-mix(in oklch, var(--color-primary) 20%, transparent);
}

.field-row {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.toggle input[type="checkbox"] {
  display: none;
}

.toggle-track {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 22px;
  border-radius: 999px;
  background: #d1d5db;
  transition: background 200ms ease;
  color: #fff;
}

.toggle input:checked + .toggle-track {
  background: var(--color-primary);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
</style>
