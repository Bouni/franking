<template>
  <v-row>
    <v-col cols="12">
      <v-chip
        variant="flat"
        color="#ffcc00"
        size="large"
      >
        {{ (internetmarke.balance / 100).toFixed(2) }} €
        <template v-slot:prepend>
                <v-img
                  width="16"
                  :src="
                      postIcon
                  "
                  class="mr-2"
                ></v-img>
        </template>
      </v-chip>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { useAppStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { onMounted } from "vue";
import postIcon from "@/assets/Post.svg";

const appStore = useAppStore();
const { internetmarke } = storeToRefs(appStore);
const { fetchBalance } = appStore;

onMounted(() => {
  fetchBalance();
});
</script>
