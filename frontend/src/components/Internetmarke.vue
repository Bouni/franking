<template>
  <v-row>
    <v-col cols="12">

        <v-chip variant="flat" color="indigo" prepend-icon="mdi-cash" size="large">
          {{ (internetmarke.balance / 100).toFixed(2) }} €
        </v-chip>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { useAppStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { onMounted } from "vue";

const appStore = useAppStore();
const { internetmarke } = storeToRefs(appStore);
const { fetchBalance } = appStore;

// Fetch data when the component loads
onMounted(() => {
  fetchBalance();
});
</script>
