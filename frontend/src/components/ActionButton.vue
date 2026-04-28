<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useAppStore, type LoadingState } from "@/store/app";

const props = defineProps<{
  icon: string;
  color: string;
  tooltip: string;
  action: LoadingState["action"];
  actionId: string | number;
  disabled?: boolean;
}>();

const emit = defineEmits(["click"]);

const store = useAppStore();
const { isLoading } = storeToRefs(store);
</script>

<template>
  <v-tooltip :text="tooltip" location="top">
    <template #activator="{ props: tooltipProps }">
      <v-btn
        v-bind="tooltipProps"
        :icon="icon"
        :color="color"
        :disabled="disabled"
        :loading="isLoading?.action === action && isLoading?.id === actionId"
        class="ma-2"
        @click="emit('click')"
      />
    </template>
  </v-tooltip>
</template>
