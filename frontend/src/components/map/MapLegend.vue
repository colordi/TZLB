<template>
  <section class="legend-card">
    <p class="legend-eyebrow">着色规则</p>
    <h3>虫口数分级</h3>

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
  gap: 0.9rem;
  height: 100%;
  padding: 1rem;
  border-radius: 1.3rem;
  background:
    linear-gradient(180deg, rgba(251, 248, 240, 0.92), rgba(243, 238, 226, 0.84));
  border: 1px solid rgba(53, 67, 48, 0.1);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.48),
    0 12px 30px rgba(25, 32, 22, 0.06);
}

.legend-eyebrow {
  margin: 0;
  font-size: 0.78rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--accent);
}

.legend-card h3 {
  margin: 0;
  font-size: 1.05rem;
}

.legend-list {
  display: grid;
  gap: 0.65rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.legend-dot {
  width: 0.9rem;
  height: 0.9rem;
  border-radius: 50%;
  box-shadow: inset 0 0 0 1px rgba(14, 16, 12, 0.14);
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
