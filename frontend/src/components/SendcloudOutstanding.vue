<template>
  <v-tooltip location="bottom">
    <template #activator="{ props: tooltipProps }">
      <!-- Sendcloud navy, a warning icon marks unpaid invoices -->
      <v-chip v-bind="tooltipProps" color="#002554" size="large" variant="flat">
        <template #prepend>
          <v-img alt="Sendcloud" class="mr-2" :src="sendcloudIcon" width="30" />
        </template>

        <v-progress-circular
          v-if="isLoading?.action === 'fetchOutstanding'"
          indeterminate
          size="16"
          width="2"
        />

        <template v-else>
          {{ formatPrice(total) }}
        </template>

        <template v-if="sendcloudOutstanding?.unpaid_count" #append>
          <v-icon class="ml-2" color="#ffca3a" icon="mdi-alert-circle" />
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
import sendcloudIcon from "@/assets/Sendcloud.svg";
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
