<script setup lang="ts">
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useAppStore } from "@/store/app";
import dhlIcon from "@/assets/DHL.svg";
import postIcon from "@/assets/Post.svg";

const props = defineProps<{
  invoiceId: string;
  countryCode: string;
  disabled?: boolean;
}>();

// Internetmarke (Deutsche Post) within Germany, DHL Warenpost International otherwise
const national = computed(() => props.countryCode?.toUpperCase() === "DE");

const store = useAppStore();
const { isLoading } = storeToRefs(store);
const { createLabel } = store;
</script>

<template>
  <v-tooltip
    :text="
      national
        ? 'Purchase Internetmarke (Deutsche Post)'
        : 'Purchase DHL Warenpost International Premium'
    "
    location="top"
  >
    <template #activator="{ props: tooltipProps }">
      <v-btn
        v-bind="tooltipProps"
        icon
        color="#ffcc00"
        class="ma-2"
        :disabled="disabled"
        :loading="
          isLoading?.action === 'createLabel' && isLoading?.id === invoiceId
        "
        @click="createLabel(invoiceId)"
      >
        <v-img
          :src="national ? postIcon : dhlIcon"
          :width="national ? 28 : 34"
          :alt="national ? 'Deutsche Post' : 'DHL'"
        />
      </v-btn>
    </template>
  </v-tooltip>
</template>
