<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";
import dhlIcon from "@/assets/DHL.svg";
import { useAppStore } from "@/store/app";

const props = defineProps<{
  invoiceId: string;
  countryCode: string;
  disabled?: boolean;
}>();

// DHL Kleinpaket within Germany, DHL Warenpost International Premium otherwise
const national = computed(() => props.countryCode?.toUpperCase() === "DE");

const store = useAppStore();
const { isLoading } = storeToRefs(store);
const { createLabel } = store;
</script>

<template>
  <v-tooltip
    location="top"
    :text="
      national
        ? 'Purchase DHL Kleinpaket'
        : 'Purchase DHL Warenpost International Premium'
    "
  >
    <template #activator="{ props: tooltipProps }">
      <v-btn
        v-bind="tooltipProps"
        class="ma-1"
        :color="disabled ? undefined : '#ffcc00'"
        :disabled="disabled"
        icon
        :loading="
          isLoading?.action === 'createLabel' && isLoading?.id === invoiceId
        "
        :variant="disabled ? 'tonal' : 'flat'"
        @click="createLabel(invoiceId)"
      >
        <v-img
          alt="DHL"
          :class="{ 'opacity-40': disabled }"
          :src="dhlIcon"
          width="34"
        />
      </v-btn>
    </template>
  </v-tooltip>
</template>
