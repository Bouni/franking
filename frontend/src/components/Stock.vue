<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";
import { useDisplay } from "vuetify";
import { type StockProduct, useAppStore } from "@/store/app";

const store = useAppStore();
const { isLoading, stock } = storeToRefs(store);
const { fetchStock, bookStock } = store;
const { xs } = useDisplay();

onMounted(fetchStock);

// Few pieces left from this many on
const LOW_STOCK = 3;

function stockLook(quantity: number | null) {
  if (quantity === null) {
    return { color: undefined, text: "not tracked", icon: "mdi-infinity" };
  }
  if (quantity <= 0) {
    return { color: "#e63946", text: `${quantity}`, icon: "mdi-close-circle" };
  }
  if (quantity <= LOW_STOCK) {
    return { color: "#d95d0f", text: `${quantity}`, icon: "mdi-alert" };
  }
  return { color: "#5a9e1b", text: `${quantity}`, icon: "mdi-check-circle" };
}

const reasons: Record<string, string> = {
  received: "Booked in",
  corrected: "Corrected",
  untracked: "Tracking stopped",
  ordered: "Order form",
  invoiced: "Invoice",
  voided: "Voided, returned",
};

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("de-DE", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

// Dialog for booking in and correcting
const dialog = ref(false);
const kind = ref<"receive" | "correct">("receive");
const product = ref<StockProduct | null>(null);
const quantity = ref<number>(1);
const tracked = ref(true);
const note = ref("");

function open(p: StockProduct, k: "receive" | "correct") {
  product.value = p;
  kind.value = k;
  quantity.value = k === "receive" ? 1 : Math.max(0, p.stock ?? 0);
  tracked.value = true;
  note.value = "";
  dialog.value = true;
}

const valid = computed(() =>
  kind.value === "receive"
    ? Number.isInteger(quantity.value) && quantity.value >= 1
    : !tracked.value ||
      (Number.isInteger(quantity.value) && quantity.value >= 0),
);

async function save() {
  if (!product.value) {
    return;
  }
  const ok = await bookStock(
    kind.value,
    product.value.id,
    kind.value === "correct" && !tracked.value ? null : quantity.value,
    note.value,
  );
  if (ok) {
    dialog.value = false;
  }
}
</script>

<template>
  <v-row>
    <v-col cols="12" lg="8">
      <v-card
        :loading="isLoading?.action === 'fetchStock'"
        prepend-icon="mdi-warehouse"
        subtitle="Orders in the order form and sent invoices are subtracted automatically"
        title="Stock"
      >
        <v-list lines="two">
          <v-list-item
            v-for="p in stock?.products ?? []"
            :key="p.id"
            :title="p.name"
          >
            <template #prepend>
              <v-chip
                class="mr-4 stock-chip"
                :color="stockLook(p.stock).color"
                :prepend-icon="stockLook(p.stock).icon"
                :variant="p.stock === null ? 'outlined' : 'flat'"
              >
                {{ stockLook(p.stock).text }}
              </v-chip>
            </template>

            <template #append>
              <div class="d-flex flex-wrap justify-end ga-2">
                <v-btn
                  color="#5a9e1b"
                  :icon="xs ? 'mdi-package-down' : undefined"
                  :loading="
                    isLoading?.action === 'bookStock' && isLoading?.id === p.id
                  "
                  :prepend-icon="xs ? undefined : 'mdi-package-down'"
                  :text="xs ? undefined : 'Book in'"
                  variant="flat"
                  @click="open(p, 'receive')"
                />

                <v-btn
                  color="#1982c4"
                  :icon="xs ? 'mdi-pencil' : undefined"
                  :prepend-icon="xs ? undefined : 'mdi-pencil'"
                  :text="xs ? undefined : 'Correct'"
                  variant="flat"
                  @click="open(p, 'correct')"
                />
              </div>
            </template>
          </v-list-item>

          <v-list-item
            v-if="stock && stock.products.length === 0"
            subtitle="Products with the category goods in Invio show up here"
            title="No goods in Invio"
          />
        </v-list>
      </v-card>

      <v-card class="mt-4" prepend-icon="mdi-history" title="History">
        <v-table density="compact">
          <thead>
            <tr>
              <th>Time</th>
              <th>Product</th>
              <th class="text-end">Change</th>
              <th class="text-end">Stock</th>
              <th>Reason</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="(entry, index) in stock?.history ?? []" :key="index">
              <td class="text-no-wrap">{{ formatDateTime(entry.at) }}</td>
              <td>{{ entry.product }}</td>

              <td
                class="text-end font-weight-bold amount"
                :class="entry.change > 0 ? 'text-success' : 'text-error'"
              >
                <span v-if="entry.change">
                  {{ entry.change > 0 ? "+" : "" }}{{ entry.change }}
                </span>
              </td>

              <td class="text-end amount">{{ entry.quantity ?? "–" }}</td>

              <td>
                {{ reasons[entry.reason] ?? entry.reason }}
                <span v-if="entry.invoice" class="text-medium-emphasis">
                  {{ entry.invoice }}
                </span>

                <div
                  v-if="entry.note"
                  class="text-caption text-medium-emphasis"
                >
                  {{ entry.note }}
                </div>
              </td>
            </tr>

            <tr v-if="!stock?.history?.length">
              <td class="text-center text-medium-emphasis py-4" colspan="5">
                Nothing booked yet
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card>
    </v-col>
  </v-row>

  <v-dialog v-model="dialog" :fullscreen="xs" max-width="460">
    <v-card
      :prepend-icon="kind === 'receive' ? 'mdi-package-down' : 'mdi-pencil'"
      :subtitle="product?.name"
      :title="kind === 'receive' ? 'Book in goods' : 'Correct stock'"
    >
      <v-card-text>
        <v-switch
          v-if="kind === 'correct'"
          v-model="tracked"
          color="primary"
          hide-details
          label="Track the stock of this product"
        />

        <v-number-input
          v-if="kind === 'receive' || tracked"
          v-model="quantity"
          class="mt-2"
          control-variant="split"
          :label="kind === 'receive' ? 'Arrived pieces' : 'Pieces in stock'"
          :min="kind === 'receive' ? 1 : 0"
        />

        <v-alert
          v-else
          class="mb-4"
          density="compact"
          type="info"
          variant="tonal"
        >
          Without tracking the product can be ordered without limit.
        </v-alert>

        <v-text-field
          v-model="note"
          counter="200"
          label="Note (optional)"
          maxlength="200"
        />
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="dialog = false">Cancel</v-btn>

        <v-btn
          color="primary"
          :disabled="!valid"
          :loading="isLoading?.action === 'bookStock'"
          variant="flat"
          @click="save"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.stock-chip {
  min-width: 72px;
  justify-content: center;
}

.amount {
  font-variant-numeric: tabular-nums;
}
</style>
