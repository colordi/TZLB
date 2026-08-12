<script setup>
import { computed, onMounted, reactive, ref } from "vue";

import {
  fetchStorageConfig,
  testStorageConnection,
  updateStorageConfig,
} from "../api/admin.js";
import { isUnauthorizedError } from "../api/http.js";
import { useToast } from "../composables/useToast.js";

import PageHeader from "@/components/common/PageHeader.vue";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";

const { error, info } = useToast();

const BACKEND_LABELS = {
  local: "本机磁盘",
  r2: "Cloudflare R2",
};

const loading = ref(false);
const saving = ref(false);
const testing = ref(false);
const secretConfigured = ref(false);
const meta = ref({ source: "env", updated_by: "", updated_at: "" });

const form = reactive({
  backend: "local",
  r2_endpoint_url: "",
  r2_access_key_id: "",
  r2_secret_access_key: "",
  r2_bucket: "",
  r2_prefix: "assets/",
});

const isR2 = computed(() => form.backend === "r2");

const sourceLabel = computed(() =>
  meta.value.source === "database" ? "管理后台配置" : "环境变量（.env）",
);

const updatedAtLabel = computed(() => {
  if (!meta.value.updated_at) return "";
  const parsed = new Date(meta.value.updated_at);
  return Number.isNaN(parsed.getTime()) ? meta.value.updated_at : parsed.toLocaleString();
});

const secretPlaceholder = computed(() =>
  secretConfigured.value ? "已配置，留空则保持不变" : "请输入 Secret Access Key",
);

function applyConfig(config) {
  form.backend = config.backend || "local";
  form.r2_endpoint_url = config.r2_endpoint_url || "";
  form.r2_access_key_id = config.r2_access_key_id || "";
  form.r2_secret_access_key = "";
  form.r2_bucket = config.r2_bucket || "";
  form.r2_prefix = config.r2_prefix || "assets/";
  secretConfigured.value = Boolean(config.r2_secret_configured);
  meta.value = {
    source: config.source || "env",
    updated_by: config.updated_by || "",
    updated_at: config.updated_at || "",
  };
}

function buildPayload() {
  return {
    backend: form.backend,
    r2_endpoint_url: form.r2_endpoint_url.trim(),
    r2_access_key_id: form.r2_access_key_id.trim(),
    r2_secret_access_key: form.r2_secret_access_key.trim(),
    r2_bucket: form.r2_bucket.trim(),
    r2_prefix: form.r2_prefix.trim() || "assets/",
  };
}

async function load() {
  if (loading.value) return;
  loading.value = true;
  try {
    applyConfig(await fetchStorageConfig());
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`加载存储配置失败：${err.message || err}`, "加载失败");
  } finally {
    loading.value = false;
  }
}

async function handleSave() {
  if (saving.value) return;
  saving.value = true;
  try {
    applyConfig(await updateStorageConfig(buildPayload()));
    info("存储配置已保存，立即生效", "保存成功");
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(`保存存储配置失败：${err.message || err}`, "保存失败");
  } finally {
    saving.value = false;
  }
}

async function handleTest() {
  if (testing.value) return;
  testing.value = true;
  try {
    const result = await testStorageConnection(buildPayload());
    info(result.message || "连接成功", "测试通过");
  } catch (err) {
    if (isUnauthorizedError(err)) return;
    error(err.message || "连接失败", "测试失败");
  } finally {
    testing.value = false;
  }
}

onMounted(() => {
  load();
});
</script>

<template>
  <div class="mx-auto w-full max-w-3xl space-y-6">
    <PageHeader
      title="存储配置"
      description="配置工单素材（点位截图、日期现场照片）的存储位置。切换到 R2 后新上传的素材写入桶中；未迁移的本地存量素材仍可正常读取（同名以桶内为准），删除会同时清理两处。"
    />

    <Card class="gap-0 p-6">
      <form class="grid gap-5" @submit.prevent="handleSave">
        <div class="grid gap-2">
          <Label for="storage-backend">存储方式</Label>
          <NativeSelect
            id="storage-backend"
            v-model="form.backend"
            data-testid="storage-backend"
            :disabled="loading"
          >
            <option value="local">本机磁盘（默认）</option>
            <option value="r2">Cloudflare R2 对象存储</option>
          </NativeSelect>
        </div>

        <template v-if="isR2">
          <div class="grid gap-2">
            <Label for="r2-endpoint">Endpoint URL</Label>
            <Input
              id="r2-endpoint"
              v-model="form.r2_endpoint_url"
              placeholder="https://<account_id>.r2.cloudflarestorage.com"
              data-testid="r2-endpoint"
            />
          </div>

          <div class="grid gap-2 sm:grid-cols-2 sm:gap-4">
            <div class="grid gap-2">
              <Label for="r2-access-key-id">Access Key ID</Label>
              <Input
                id="r2-access-key-id"
                v-model="form.r2_access_key_id"
                placeholder="R2 API Token 的 Access Key ID"
                data-testid="r2-access-key-id"
              />
            </div>
            <div class="grid gap-2">
              <Label for="r2-secret-access-key">Secret Access Key</Label>
              <Input
                id="r2-secret-access-key"
                v-model="form.r2_secret_access_key"
                type="password"
                :placeholder="secretPlaceholder"
                data-testid="r2-secret-access-key"
              />
            </div>
          </div>

          <div class="grid gap-2 sm:grid-cols-2 sm:gap-4">
            <div class="grid gap-2">
              <Label for="r2-bucket">Bucket 名称</Label>
              <Input
                id="r2-bucket"
                v-model="form.r2_bucket"
                placeholder="例如 tzlb-assets"
                data-testid="r2-bucket"
              />
            </div>
            <div class="grid gap-2">
              <Label for="r2-prefix">Key 前缀</Label>
              <Input
                id="r2-prefix"
                v-model="form.r2_prefix"
                placeholder="assets/"
                data-testid="r2-prefix"
              />
            </div>
          </div>
        </template>

        <p class="text-sm text-muted-foreground" data-testid="storage-status">
          当前生效：{{ BACKEND_LABELS[form.backend] || form.backend }}（配置来源：{{ sourceLabel }}）
          <template v-if="meta.updated_by">
            · 最近由 {{ meta.updated_by }} 更新于 {{ updatedAtLabel }}
          </template>
        </p>

        <div class="flex items-center justify-end gap-2">
          <Button
            v-if="isR2"
            type="button"
            variant="outline"
            :disabled="testing || saving"
            data-testid="storage-test"
            @click="handleTest"
          >
            {{ testing ? "测试中…" : "测试连接" }}
          </Button>
          <Button type="submit" :disabled="saving || loading" data-testid="storage-save">
            {{ saving ? "保存中…" : "保存" }}
          </Button>
        </div>
      </form>
    </Card>
  </div>
</template>
