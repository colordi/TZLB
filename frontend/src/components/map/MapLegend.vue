<template>
  <section class="legend-card">
    <div class="legend-head">
      <p class="ui-eyebrow">着色规则</p>
      <h3>虫口数分级</h3>
      <p class="legend-note">用于判读点位风险等级与虫口数区间。</p>
    </div>

    <div class="legend-list">
      <div class="legend-item">
        <span class="legend-dot level-0"></span>
        <span>0 或缺失</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot level-1"></span>
        <span>1 - 10</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot level-2"></span>
        <span>11 - 50</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot level-3"></span>
        <span>50 以上</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.legend-card {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface-base);
  box-shadow: var(--shadow-card);
}

.legend-head {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.legend-card h3 {
  font-size: 1rem;
  font-weight: 600;
}

.legend-note {
  color: var(--muted);
  font-size: 0.875rem;
  line-height: 1.6;
}

.legend-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-card);
  font-size: 0.875rem;
}

.legend-dot {
  width: 0.875rem;
  height: 0.875rem;
  border-radius: 50%;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.1);
}

.level-0 {
  background: #94a3b8;
}

.level-1 {
  background: #22c55e;
}

.level-2 {
  background: #f59e0b;
}

.level-3 {
  background: #ef4444;
}
</style>
