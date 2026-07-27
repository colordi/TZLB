<script setup>
import { X } from "@lucide/vue";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { NativeSelect } from "@/components/ui/native-select";
import {
  SITE_ADD_KIND_OTHER_PEST,
} from "../../composables/map/constants.js";

defineProps({
  siteAddTitle: { type: String, default: "" },
  siteLocationText: { type: String, default: "" },
  activeSiteAddKind: { type: String, default: "" },
  siteForm: { type: Object, required: true },
  isSavingSite: { type: Boolean, default: false },
  canSubmitSite: { type: Boolean, default: false },
  siteCodeError: { type: String, default: "" },
  otherPestSiteCodeExample: { type: String, default: "QT0001" },
  otherPestSiteLocalities: { type: Array, default: () => [] },
  otherPestSiteCodeHintText: { type: String, default: "" },
  otherPestSiteCodeHint: { type: Object, default: null },
  loadingOtherPestSiteCodeHint: { type: Boolean, default: false },
  whiteMothSiteCodeExample: { type: String, default: "MQ001" },
  resolvedWhiteMothSiteLocality: { type: String, default: "" },
  matchedWhiteMothSitePrefix: { type: String, default: "" },
  whiteMothSiteCodeHintText: { type: String, default: "" },
  whiteMothSiteCodeHint: { type: Object, default: null },
  loadingWhiteMothSiteCodeHint: { type: Boolean, default: false },
});

const emit = defineEmits([
  "cancel",
  "submit",
  "update:code",
  "update:siteName",
  "update:locality",
  "normalize-code",
  "apply-suggested-code",
]);

const otherPestKind = SITE_ADD_KIND_OTHER_PEST;
</script>

<template>
  <aside class="site-add-drawer" :aria-label="siteAddTitle">
    <article class="site-add-card">
      <header class="detail-header">
        <span class="detail-title">{{ siteAddTitle }}</span>
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          class="shrink-0 text-muted-foreground"
          aria-label="关闭新增点位"
          :disabled="isSavingSite"
          @click="emit('cancel')"
        >
          <X aria-hidden="true" />
        </Button>
      </header>
      <div class="detail-divider"></div>

      <form class="site-add-form" @submit.prevent="emit('submit')">
        <div class="site-add-location">
          <span class="detail-label">坐标</span>
          <strong data-testid="site-add-location-text">
            {{ siteLocationText }}
          </strong>
        </div>

        <template v-if="activeSiteAddKind === otherPestKind">
          <label class="site-add-field">
            <span>编号</span>
            <Input
              :model-value="siteForm.code"
              data-testid="other-pest-site-code"
              inputmode="text"
              autocomplete="off"
              :placeholder="otherPestSiteCodeExample"
              :disabled="isSavingSite"
              @blur="emit('normalize-code')"
              @update:model-value="emit('update:code', $event)"
            />
            <small
              v-if="siteCodeError"
              class="text-xs text-destructive"
              data-testid="other-pest-site-code-error"
            >
              {{ siteCodeError }}
            </small>
          </label>

          <label class="site-add-field">
            <span>属地</span>
            <NativeSelect
              :model-value="siteForm.locality"
              data-testid="other-pest-site-locality-select"
              :disabled="isSavingSite"
              @update:model-value="emit('update:locality', $event)"
            >
              <option value="">请选择乡镇街道</option>
              <option
                v-for="locality in otherPestSiteLocalities"
                :key="locality"
                :value="locality"
              >
                {{ locality }}
              </option>
            </NativeSelect>
          </label>

          <div
            class="site-add-location site-add-code-hint"
            data-testid="other-pest-site-code-hint"
          >
            <span class="detail-label">编号提示</span>
            <strong data-testid="other-pest-site-code-hint-text">
              {{ otherPestSiteCodeHintText }}
            </strong>
            <Button
              v-if="otherPestSiteCodeHint?.suggested_next_code && !loadingOtherPestSiteCodeHint"
              type="button"
              variant="outline"
              size="xs"
              class="self-start"
              data-testid="other-pest-site-fill-suggested-code"
              :disabled="isSavingSite"
              @click="emit('apply-suggested-code')"
            >
              填入建议编号
            </Button>
          </div>
        </template>

        <template v-else>
          <label class="site-add-field">
            <span>编号</span>
            <Input
              :model-value="siteForm.code"
              data-testid="white-moth-site-code"
              inputmode="text"
              autocomplete="off"
              :placeholder="whiteMothSiteCodeExample"
              :disabled="isSavingSite"
              @blur="emit('normalize-code')"
              @update:model-value="emit('update:code', $event)"
            />
            <small
              v-if="siteCodeError"
              class="text-xs text-destructive"
              data-testid="white-moth-site-code-error"
            >
              {{ siteCodeError }}
            </small>
          </label>

          <div class="site-add-location">
            <span class="detail-label">自动识别属地</span>
            <strong data-testid="white-moth-site-locality">
              {{ resolvedWhiteMothSiteLocality || "待识别" }}
            </strong>
          </div>

          <div
            v-if="matchedWhiteMothSitePrefix"
            class="site-add-location site-add-code-hint"
            data-testid="white-moth-site-code-hint"
          >
            <span class="detail-label">编号提示</span>
            <strong data-testid="white-moth-site-code-hint-text">
              {{ whiteMothSiteCodeHintText }}
            </strong>
            <Button
              v-if="whiteMothSiteCodeHint?.suggested_next_code && !loadingWhiteMothSiteCodeHint"
              type="button"
              variant="outline"
              size="xs"
              class="self-start"
              data-testid="white-moth-site-fill-suggested-code"
              :disabled="isSavingSite"
              @click="emit('apply-suggested-code')"
            >
              填入建议编号
            </Button>
          </div>
        </template>

        <label class="site-add-field">
          <span>点位名称</span>
          <Input
            :model-value="siteForm.siteName"
            data-testid="site-add-name"
            autocomplete="off"
            :disabled="isSavingSite"
            placeholder="可不填写"
            @update:model-value="emit('update:siteName', $event)"
          />
        </label>

        <div class="site-add-actions">
          <Button
            type="submit"
            data-testid="site-add-submit"
            :disabled="!canSubmitSite"
          >
            {{ isSavingSite ? "保存中" : "保存点位" }}
          </Button>
          <Button
            type="button"
            variant="outline"
            :disabled="isSavingSite"
            @click="emit('cancel')"
          >
            取消
          </Button>
        </div>
      </form>
    </article>
  </aside>
</template>
