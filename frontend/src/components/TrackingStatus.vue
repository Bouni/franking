<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  label: any;
}>();

// Latest Sendcloud tracking event, stored by the backend's tracking check
const tracking = computed(() => props.label?.tracking);

const look = computed(() => {
  const t = tracking.value;
  if (t?.phase === "delivered") {
    return { color: "#8ac926", icon: "mdi-package-variant-closed-check" };
  }
  if (t?.status_type === "error") {
    return { color: "#e63946", icon: "mdi-alert-octagon" };
  }
  if (t?.status_type === "warning") {
    return { color: "#ff924c", icon: "mdi-alert" };
  }
  return { color: "#1982c4", icon: "mdi-truck-delivery" };
});

const details = computed(() => {
  const t = tracking.value;
  if (!t) {
    return "";
  }
  const parts = [];
  if (t.event_at) {
    parts.push(`Since ${new Date(t.event_at).toLocaleString("de-DE")}`);
  }
  if (t.expected_delivery_date) {
    parts.push(
      `expected ${new Date(t.expected_delivery_date).toLocaleDateString("de-DE")}`,
    );
  }
  return parts.join(", ");
});
</script>

<template>
  <v-tooltip v-if="tracking" location="top" :text="details">
    <template #activator="{ props: tooltipProps }">
      <v-chip
        v-bind="tooltipProps"
        class="tracking-chip"
        :color="look.color"
        :href="label.tracking_url"
        :prepend-icon="look.icon"
        size="small"
        target="_blank"
        variant="flat"
      >
        <span class="text-truncate">{{ tracking.description }}</span>
      </v-chip>
    </template>
  </v-tooltip>
</template>

<style scoped>
.tracking-chip {
  max-width: 100%;
}
</style>
