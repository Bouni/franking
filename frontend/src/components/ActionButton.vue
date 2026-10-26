<script setup lang="ts">
import { storeToRefs } from "pinia";
import { type LoadingState, useAppStore } from "@/store/app";

defineProps<{
  icon: string;
  color: string;
  tooltip: string;
  action: LoadingState["action"];
  actionId: string | number;
  disabled?: boolean;
  variant?: "flat" | "tonal" | "outlined" | "text";
}>();

const emit = defineEmits(["click"]);

const store = useAppStore();
const { isLoading } = storeToRefs(store);
</script>

<template>
  <v-tooltip location="top" :text="tooltip">
    <template #activator="{ props: tooltipProps }">
      <v-btn
        v-bind="tooltipProps"
        class="ma-1"
        :color="color"
        :disabled="disabled"
        :icon="icon"
        :loading="isLoading?.action === action && isLoading?.id === actionId"
        :variant="variant ?? 'flat'"
        @click="emit('click')"
      />
    </template>
  </v-tooltip>
</template>
