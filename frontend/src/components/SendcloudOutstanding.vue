<template>
  <v-tooltip location="bottom">
    <template #activator="{ props: tooltipProps }">
      <v-chip
        v-bind="tooltipProps"
        :color="sendcloudOutstanding?.unpaid_count ? '#ffca3a' : '#8ac926'"
        prepend-icon="mdi-receipt-text-outline"
        size="large"
        variant="flat"
      >
        <v-progress-circular
          v-if="isLoading?.action === 'fetchOutstanding'"
          indeterminate
          size="16"
          width="2"
        />

        <template v-else>
          {{ formatPrice(total) }}
        </template>
      </v-chip>
    </template>

    <div>Sendcloud shipping costs</div>

    <div>
      Not invoiced yet: {{ formatPrice(sendcloudOutstanding?.open ?? 0) }}
    </div>

    <div>
      Unpaid invoices ({{ sendcloudOutstanding?.unpaid_count ?? 0 }}):
      {{ formatPrice(sendcloudOutstanding?.unpaid ?? 0) }}
    </div>
  </v-tooltip>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted } from "vue";
import { formatPrice } from "@/invoice";
import { useAppStore } from "@/store/app";

const appStore = useAppStore();
const { sendcloudOutstanding, isLoading } = storeToRefs(appStore);
const { fetchOutstanding } = appStore;

const total = computed(
  () =>
    (sendcloudOutstanding.value?.open ?? 0) +
    (sendcloudOutstanding.value?.unpaid ?? 0),
);

onMounted(() => {
  fetchOutstanding();
});
</script>
