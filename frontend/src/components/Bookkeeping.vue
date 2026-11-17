<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";
import { useDisplay } from "vuetify";
import {
  type Entry,
  type EntryData,
  type EntryKind,
  useBookkeepingStore,
} from "@/store/bookkeeping";

const store = useBookkeepingStore();
const { data, year, loading } = storeToRefs(store);
const { xs } = useDisplay();

onMounted(store.fetch);
watch(year, store.fetch);

const years = computed(() => data.value?.years ?? [year.value]);

// Suggestions, the categories end up in the report for the tax advisor
const DEFAULT_CATEGORIES = {
  expense: [
    "Wareneinkauf",
    "Versandkosten",
    "Verpackung",
    "Gebühren",
    "Software",
    "Werbung",
    "Büromaterial",
    "Sonstiges",
  ],
  income: ["Sonstiges"],
};

function categories(kind: EntryKind) {
  const used = (kind === "expense" ? data.value?.expenses : data.value?.income)
    ?.map((e) => e.category)
    .filter(Boolean);
  return [
    ...new Set([...DEFAULT_CATEGORIES[kind], ...(used ?? [])]),
  ].toSorted();
}

const money = new Intl.NumberFormat("de-DE", {
  style: "currency",
  currency: "EUR",
});

function formatMoney(value: number) {
  return money.format(value);
}

function formatDate(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("de-DE");
}

function today() {
  const now = new Date();
  return [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
}

const missingReceipts = computed(
  () => data.value?.expenses.filter((e) => !e.has_receipt).length ?? 0,
);

const showInvoices = ref(false);

// Dialog for adding and editing an entry
const dialog = ref(false);
const editing = ref<Entry | null>(null);
const form = ref<EntryData>(blank("expense"));
const file = ref<File | null>(null);
const dropReceipt = ref(false);

function blank(kind: EntryKind): EntryData {
  // Default to a day in the year that's shown
  const day = today().startsWith(`${year.value}-`)
    ? today()
    : `${year.value}-12-31`;
  return {
    kind,
    date: day,
    description: "",
    party: "",
    category: "",
    amount: 0,
    vat: 0,
    note: "",
  };
}

function add(kind: EntryKind) {
  editing.value = null;
  form.value = blank(kind);
  file.value = null;
  dropReceipt.value = false;
  dialog.value = true;
}

function edit(entry: Entry) {
  editing.value = entry;
  form.value = {
    kind: entry.kind,
    date: entry.date,
    description: entry.description,
    party: entry.party,
    category: entry.category,
    amount: entry.amount,
    vat: entry.vat,
    note: entry.note,
  };
  file.value = null;
  dropReceipt.value = false;
  dialog.value = true;
}

const valid = computed(
  () =>
    !!form.value.date &&
    form.value.description.trim() !== "" &&
    form.value.amount > 0 &&
    (form.value.vat ?? 0) >= 0 &&
    (form.value.vat ?? 0) <= form.value.amount,
);

const saving = computed(
  () => loading.value?.action === "save" || loading.value?.action === "receipt",
);

async function save() {
  const saved = await store.save(
    { ...form.value, vat: form.value.vat || 0 },
    editing.value?.id,
  );
  if (!saved) {
    return;
  }
  // The entry exists now, a failed upload leaves it there to try again
  let ok = true;
  if (file.value) {
    ok = await store.uploadReceipt(saved.id, file.value);
  } else if (dropReceipt.value && saved.has_receipt) {
    ok = await store.removeReceipt(saved.id);
  }
  await store.fetch();
  if (ok) {
    dialog.value = false;
  } else {
    editing.value =
      data.value?.expenses.find((e) => e.id === saved.id) ?? editing.value;
  }
}

// Delete with a confirmation
const confirmDelete = ref<Entry | null>(null);

async function remove() {
  if (confirmDelete.value) {
    await store.remove(confirmDelete.value.id);
    confirmDelete.value = null;
  }
}

function openReceipt(entry: Entry) {
  window.open(store.receiptUrl(entry.id), "_blank");
}

function downloadReport(receipts: boolean) {
  window.open(store.reportUrl(receipts), "_blank");
}
</script>

<template>
  <v-row>
    <v-col cols="12" lg="8">
      <v-card
        :loading="loading?.action === 'fetch'"
        prepend-icon="mdi-book-open-variant"
        subtitle="Paid invoices from Invio count as income in the year they were paid"
        title="Bookkeeping"
      >
        <template #append>
          <v-select
            v-model="year"
            density="compact"
            hide-details
            :items="years"
            label="Year"
            style="min-width: 110px"
            variant="outlined"
          />
        </template>

        <v-card-text>
          <v-row dense>
            <v-col cols="12" sm="4">
              <v-sheet class="pa-3" color="green-lighten-5" rounded="lg">
                <div class="text-caption">Income</div>

                <div class="text-h6 amount text-success">
                  {{ formatMoney(data?.totals.income ?? 0) }}
                </div>
              </v-sheet>
            </v-col>

            <v-col cols="12" sm="4">
              <v-sheet class="pa-3" color="red-lighten-5" rounded="lg">
                <div class="text-caption">Expenses</div>

                <div class="text-h6 amount text-error">
                  {{ formatMoney(data?.totals.expenses ?? 0) }}
                </div>
              </v-sheet>
            </v-col>

            <v-col cols="12" sm="4">
              <v-sheet class="pa-3" color="blue-lighten-5" rounded="lg">
                <div class="text-caption">
                  {{ (data?.totals.result ?? 0) < 0 ? "Loss" : "Surplus" }}
                </div>

                <div class="text-h6 amount">
                  {{ formatMoney(data?.totals.result ?? 0) }}
                </div>
              </v-sheet>
            </v-col>
          </v-row>

          <v-alert
            v-if="missingReceipts"
            class="mt-4"
            density="compact"
            type="warning"
            variant="tonal"
          >
            {{ missingReceipts }}
            {{ missingReceipts === 1 ? "expense has" : "expenses have" }} no
            receipt yet.
          </v-alert>
        </v-card-text>

        <v-card-actions>
          <v-spacer />

          <v-menu>
            <template #activator="{ props }">
              <v-btn
                v-bind="props"
                color="primary"
                prepend-icon="mdi-file-pdf-box"
                variant="flat"
              >
                Report {{ year }}
              </v-btn>
            </template>

            <v-list>
              <v-list-item
                prepend-icon="mdi-paperclip"
                subtitle="Receipts appended, for the tax advisor"
                title="With receipts"
                @click="downloadReport(true)"
              />

              <v-list-item
                prepend-icon="mdi-file-document-outline"
                subtitle="Just the summary and the lists"
                title="Without receipts"
                @click="downloadReport(false)"
              />
            </v-list>
          </v-menu>
        </v-card-actions>
      </v-card>

      <!-- Income -->
      <v-card class="mt-4" prepend-icon="mdi-cash-plus" title="Income">
        <template #append>
          <v-btn
            color="#5a9e1b"
            :icon="xs ? 'mdi-plus' : undefined"
            :prepend-icon="xs ? undefined : 'mdi-plus'"
            :text="xs ? undefined : 'Add income'"
            variant="flat"
            @click="add('income')"
          />
        </template>

        <v-table density="compact">
          <thead>
            <tr>
              <th>Date</th>
              <th>Description</th>
              <th class="d-none d-sm-table-cell">Category</th>
              <th class="text-end">Amount</th>
              <th />
            </tr>
          </thead>

          <tbody>
            <tr class="cursor-pointer" @click="showInvoices = !showInvoices">
              <td class="text-medium-emphasis">{{ year }}</td>

              <td>
                <v-icon
                  :icon="
                    showInvoices ? 'mdi-chevron-down' : 'mdi-chevron-right'
                  "
                  size="small"
                />
                Invoices from Invio
                <span class="text-medium-emphasis">
                  ({{ data?.invoices.length ?? 0 }})
                </span>
              </td>

              <td class="d-none d-sm-table-cell" />

              <td class="text-end amount font-weight-bold">
                {{ formatMoney(data?.totals.invoices ?? 0) }}
              </td>

              <td />
            </tr>

            <template v-if="showInvoices">
              <tr
                v-for="invoice in data?.invoices ?? []"
                :key="invoice.id"
                class="invoice-row"
              >
                <td class="text-no-wrap">{{ formatDate(invoice.date) }}</td>

                <td>
                  {{ invoice.number }}
                  <span class="text-medium-emphasis">{{
                    invoice.customer
                  }}</span>
                </td>

                <td class="d-none d-sm-table-cell text-medium-emphasis">
                  {{ invoice.method }}
                </td>

                <td class="text-end amount">
                  {{ formatMoney(invoice.amount) }}
                </td>

                <td />
              </tr>
            </template>

            <tr v-for="entry in data?.income ?? []" :key="entry.id">
              <td class="text-no-wrap">{{ formatDate(entry.date) }}</td>

              <td>
                {{ entry.description }}
                <span v-if="entry.party" class="text-medium-emphasis">
                  {{ entry.party }}
                </span>

                <div
                  v-if="entry.note"
                  class="text-caption text-medium-emphasis"
                >
                  {{ entry.note }}
                </div>
              </td>

              <td class="d-none d-sm-table-cell">{{ entry.category }}</td>
              <td class="text-end amount">{{ formatMoney(entry.amount) }}</td>

              <td class="text-end text-no-wrap">
                <v-btn
                  icon="mdi-pencil"
                  size="small"
                  variant="text"
                  @click="edit(entry)"
                />

                <v-btn
                  icon="mdi-delete"
                  size="small"
                  variant="text"
                  @click="confirmDelete = entry"
                />
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card>

      <!-- Expenses -->
      <v-card class="mt-4" prepend-icon="mdi-cash-minus" title="Expenses">
        <template #append>
          <v-btn
            color="#e63946"
            :icon="xs ? 'mdi-plus' : undefined"
            :prepend-icon="xs ? undefined : 'mdi-plus'"
            :text="xs ? undefined : 'Add expense'"
            variant="flat"
            @click="add('expense')"
          />
        </template>

        <v-table density="compact">
          <thead>
            <tr>
              <th>Date</th>
              <th>Description</th>
              <th class="d-none d-sm-table-cell">Category</th>
              <th class="text-end">Amount</th>
              <th class="text-center">Receipt</th>
              <th />
            </tr>
          </thead>

          <tbody>
            <tr v-for="entry in data?.expenses ?? []" :key="entry.id">
              <td class="text-no-wrap">{{ formatDate(entry.date) }}</td>

              <td>
                {{ entry.description }}
                <span v-if="entry.party" class="text-medium-emphasis">
                  {{ entry.party }}
                </span>

                <div
                  v-if="entry.note"
                  class="text-caption text-medium-emphasis"
                >
                  {{ entry.note }}
                </div>
              </td>

              <td class="d-none d-sm-table-cell">{{ entry.category }}</td>

              <td class="text-end amount">
                {{ formatMoney(entry.amount) }}
                <div v-if="entry.vat" class="text-caption text-medium-emphasis">
                  incl. {{ formatMoney(entry.vat) }} VAT
                </div>
              </td>

              <td class="text-center">
                <v-btn
                  v-if="entry.has_receipt"
                  color="#5a9e1b"
                  icon="mdi-paperclip"
                  size="small"
                  :title="entry.receipt_name ?? 'Receipt'"
                  variant="text"
                  @click="openReceipt(entry)"
                />

                <v-btn
                  v-else
                  color="#d95d0f"
                  icon="mdi-paperclip-off"
                  size="small"
                  title="No receipt, add one"
                  variant="text"
                  @click="edit(entry)"
                />
              </td>

              <td class="text-end text-no-wrap">
                <v-btn
                  icon="mdi-pencil"
                  size="small"
                  variant="text"
                  @click="edit(entry)"
                />

                <v-btn
                  icon="mdi-delete"
                  size="small"
                  variant="text"
                  @click="confirmDelete = entry"
                />
              </td>
            </tr>

            <tr v-if="data && data.expenses.length > 0">
              <td class="font-weight-bold" colspan="3">Total</td>

              <td class="text-end amount font-weight-bold">
                {{ formatMoney(data.totals.expenses) }}
              </td>

              <td colspan="2" />
            </tr>

            <tr v-if="!data?.expenses.length">
              <td class="text-center text-medium-emphasis py-4" colspan="6">
                No expenses in {{ year }}
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card>
    </v-col>
  </v-row>

  <v-dialog v-model="dialog" :fullscreen="xs" max-width="520">
    <v-card
      :prepend-icon="
        form.kind === 'expense' ? 'mdi-cash-minus' : 'mdi-cash-plus'
      "
      :title="
        (editing ? 'Edit ' : 'Add ') +
        (form.kind === 'expense' ? 'expense' : 'income')
      "
    >
      <v-card-text>
        <v-text-field v-model="form.date" label="Date" type="date" />

        <v-text-field
          v-model="form.description"
          counter="200"
          label="Description"
          maxlength="200"
        />

        <v-text-field
          v-model="form.party"
          :label="
            form.kind === 'expense' ? 'Paid to (optional)' : 'From (optional)'
          "
          maxlength="200"
        />

        <v-combobox
          v-model="form.category"
          :items="categories(form.kind)"
          label="Category"
          maxlength="100"
        />

        <v-row dense>
          <v-col cols="12" sm="6">
            <v-number-input
              v-model="form.amount"
              control-variant="hidden"
              label="Amount (gross)"
              :min="0"
              :precision="2"
              suffix="€"
            />
          </v-col>

          <v-col v-if="form.kind === 'expense'" cols="12" sm="6">
            <v-number-input
              v-model="form.vat"
              control-variant="hidden"
              label="Of which VAT (optional)"
              :min="0"
              :precision="2"
              suffix="€"
            />
          </v-col>
        </v-row>

        <v-text-field
          v-model="form.note"
          counter="500"
          label="Note (optional)"
          maxlength="500"
        />

        <template v-if="form.kind === 'expense'">
          <div
            v-if="editing?.has_receipt && !dropReceipt && !file"
            class="d-flex align-center mb-4"
          >
            <v-icon class="mr-2" color="#5a9e1b" icon="mdi-paperclip" />

            <a
              class="text-truncate"
              :href="store.receiptUrl(editing.id)"
              target="_blank"
            >
              {{ editing.receipt_name ?? "Receipt" }}
            </a>

            <v-spacer />

            <v-btn
              color="error"
              size="small"
              variant="text"
              @click="dropReceipt = true"
            >
              Remove
            </v-btn>
          </div>

          <v-file-input
            v-model="file"
            accept="application/pdf,image/png,image/jpeg"
            hint="PDF, PNG or JPEG, up to 20 MB"
            :label="
              editing?.has_receipt ? 'Replace receipt' : 'Receipt (optional)'
            "
            persistent-hint
            prepend-icon="mdi-paperclip"
          />

          <v-alert
            v-if="dropReceipt && !file"
            class="mt-4"
            density="compact"
            type="info"
            variant="tonal"
          >
            The receipt is removed when you save.
          </v-alert>
        </template>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="dialog = false">Cancel</v-btn>

        <v-btn
          color="primary"
          :disabled="!valid"
          :loading="saving"
          variant="flat"
          @click="save"
        >
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-dialog
    max-width="420"
    :model-value="!!confirmDelete"
    @update:model-value="confirmDelete = null"
  >
    <v-card prepend-icon="mdi-delete" title="Delete entry?">
      <v-card-text>
        {{ confirmDelete?.description }},
        {{ formatMoney(confirmDelete?.amount ?? 0) }}
        <template v-if="confirmDelete?.has_receipt"> and its receipt </template>
        will be deleted.
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="confirmDelete = null">Cancel</v-btn>

        <v-btn
          color="error"
          :loading="loading?.action === 'delete'"
          variant="flat"
          @click="remove"
        >
          Delete
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.amount {
  font-variant-numeric: tabular-nums;
}

.invoice-row td {
  font-size: 0.8125rem;
}
</style>
