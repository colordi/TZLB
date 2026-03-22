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
  display: grid;
  gap: 0.95rem;
  padding: 1rem;
  border: 1px solid var(--line-strong);
  border-radius: var(--radius-lg);
  background: var(--surface-base);
  box-shadow: var(--shadow-card);
}

.legend-head {
  display: grid;
  gap: 0.3rem;
}

.legend-card h3 {
  font-size: 1.08rem;
}

.legend-note {
  color: var(--muted);
  line-height: 1.6;
}

.legend-list {
  display: grid;
  gap: 0.65rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.75rem 0.85rem;
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-md);
  background: var(--surface-card);
}

.legend-dot {
  width: 0.95rem;
  height: 0.95rem;
  border-radius: 50%;
  box-shadow: inset 0 0 0 1px rgba(20, 27, 21, 0.12);
}

.level-0 {
  background: #c2c7bf;
}

.level-1 {
  background: #9eb76a;
}

.level-2 {
  background: #e19d46;
}

.level-3 {
  background: #ba4b33;
}
</style>
