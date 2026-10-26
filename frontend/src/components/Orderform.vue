<template>
  <v-row>
    <v-col cols="12" lg="6">
      <v-card title="Info">
        <v-card-text>
          You're about to order a BSH Board, so let me clarify a few things.
          <ul>
            <li>
              This is a side project for me, so I have no interest in setting up
              a real webshop for it. Therefore I created this little order form
              to help me process orders more conveniently.
            </li>

            <li>
              Once you placed an order, I'll manually send you an invoice.
            </li>

            <li>I only send out invoices if I have boards available.</li>

            <li>
              Once you paid the invoice, I usually ship the next business day.
            </li>
          </ul>
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="12" lg="6">
      <v-card title="FAQ">
        <v-card-text>
          <v-row>
            <v-col cols="12" lg="6">
              <v-card variant="tonal">
                <v-card-text>
                  <div class="mb-2">
                    <v-icon icon="mdi-chat-question" /> What connector type do I
                    need?
                  </div>

                  <div>
                    <v-icon icon="mdi-chat-alert" /> You need one 3-pin RAST
                    connector for the board itself. You will also need a 3-pin
                    or a 4-pin RAST connector for the machine side. Which one
                    depends on your model but there is definitiv list which
                    model needs which connector.
                  </div>
                </v-card-text>
              </v-card>
            </v-col>

            <v-col cols="12" lg="6">
              <v-card variant="tonal">
                <v-card-text>
                  <div class="mb-2">
                    <v-icon icon="mdi-chat-question" /> Can you sell me ready to
                    use RAST connection cables?
                  </div>

                  <div>
                    <v-icon icon="mdi-chat-alert" /> Unfortunately, no. Not at
                    this point, maybe I can in the future but there are no plans
                    for this now. For me 3x0.34mm² cable worked out pretty well.
                    Alternatively you can use single wires of this size.
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-col>

    <v-col class="d-none d-lg-block" cols="12" lg="2" />

    <v-col cols="12" lg="8">
      <v-card class="pa-5">
        <v-form ref="form" v-model="isFormValid" @submit.prevent="handleSubmit">
          <v-card class="pa-4 mb-3" title="Adress data" variant="outlined">
            <v-row density="compact">
              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.firstname"
                  hint="* Required field"
                  label="First Name"
                  persistent-hint
                  :rules="[rules.required]"
                />
              </v-col>

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.lastname"
                  hint="* Required field"
                  label="Last Name"
                  persistent-hint
                  :rules="[rules.required]"
                />
              </v-col>

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.email"
                  hint="* Required field"
                  label="Email Address"
                  persistent-hint
                  :rules="[rules.required, rules.email]"
                />
              </v-col>

              <v-col cols="12" lg="6" />

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.address"
                  hint="* Required field"
                  label="Address"
                  persistent-hint
                  :rules="[rules.required]"
                />
              </v-col>

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.city"
                  hint="* Required field"
                  label="City"
                  persistent-hint
                  :rules="[rules.required]"
                />
              </v-col>

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.postalcode"
                  hint="* Required field"
                  label="Postal code"
                  persistent-hint
                  :rules="[rules.required]"
                />
              </v-col>

              <v-col cols="12" lg="6">
                <v-autocomplete
                  v-model="order.country"
                  clearable
                  hint="* Required field"
                  item-title="name"
                  item-value="code"
                  :items="COUNTRIES"
                  label="Select Country"
                  persistent-hint
                  :rules="[rules.required]"
                >
                  <template #item="{ props, item }">
                    <v-list-item v-bind="props" :title="item.name">
                      <template #prepend>
                        <span
                          class="text-h6 mr-2"
                          :class="`fi fi-${item.code.toLowerCase()}`"
                          style="border-radius: 2px"
                        />
                      </template>
                    </v-list-item>
                  </template>

                  <template #selection="{ item }">
                    <span
                      class="text-h6 mr-2"
                      :class="`fi fi-${order.country.toLowerCase()}`"
                      style="border-radius: 2px"
                    />

                    <span>{{ item.name }}</span>
                  </template>
                </v-autocomplete>
              </v-col>
            </v-row>
          </v-card>

          <v-card class="pa-4" title="Items" variant="outlined">
            <v-row
              v-for="item in order.items"
              :key="item.article_number"
              density="compact"
            >
              <v-col cols="12" lg="6" sm="6">
                <div class="item-caption">{{ item.name }}</div>
              </v-col>

              <v-col cols="12" lg="2" sm="2">
                <div class="item-caption">{{ item.price.toFixed(2) }}€</div>
              </v-col>

              <v-col cols="12" lg="2" sm="2">
                <div class="item-caption">
                  {{ (item.quantity * item.price).toFixed(2) }}€
                </div>
              </v-col>

              <v-col cols="12" lg="2" sm="2">
                <v-text-field
                  v-model="item.quantity"
                  label="Quantity"
                  type="number"
                />
              </v-col>
            </v-row>

            <v-row density="compact">
              <v-col cols="12" lg="6" sm="6">
                <div class="item-caption">Sum</div>
              </v-col>

              <v-col cols="12" lg="2" sm="2" />

              <v-col cols="12" lg="2" sm="2">
                <div class="item-caption">{{ subtotal.toFixed(2) }}€</div>
              </v-col>

              <v-col cols="12" lg="2" sm="2" />
            </v-row>
          </v-card>

          <v-row density="compact">
            <v-col class="text-center" cols="12">
              <v-btn class="mt-4" color="primary" type="submit">
                Submit Order
              </v-btn>
            </v-col>
          </v-row>
        </v-form>
      </v-card>
    </v-col>

    <v-col class="d-none d-lg-block" cols="12" lg="2" />
  </v-row>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { COUNTRIES } from "@/constants/countries";
import { useOrderStore } from "@/store/order";

const orderStore = useOrderStore();

const form = ref(null);
const isFormValid = ref(false);

const order = ref({
  firstname: "",
  lastname: "",
  email: "",
  address: "",
  city: "",
  postalcode: "",
  country: "",
  items: [
    { name: "BSH Board", article_number: "1", price: 15, quantity: 0 },
    {
      name: "RAST Connector 3-pin",
      article_number: "2",
      price: 1,
      quantity: 0,
    },
    {
      name: "RAST Connector 4-pin",
      article_number: "3",
      price: 1,
      quantity: 0,
    },
    { name: "BSH Board Case", article_number: "4", price: 10, quantity: 0 },
  ],
});

// Calculate subtotal for items only
const subtotal = computed(() => {
  return order.value.items.reduce((sum, item) => {
    return sum + item.price * item.quantity;
  }, 0);
});

// Validation rules array of functions returning true or an error message string
const rules = {
  required: (val: unknown) => !!val || "This field is required.",
  email: (val: string) =>
    /.[^\n\r@\u2028\u2029]*@.+\..+/.test(val) ||
    "Must be a valid email address.",
  minQuantity: (val: number) => val >= 1 || "Quantity must be at least 1.",
};

type FormInstance = {
  validate: () => Promise<{ valid: boolean }>;
};

async function handleSubmit() {
  const formRef = form.value as FormInstance | null;
  const { valid } = (await formRef?.validate()) ?? { valid: false };

  if (!valid) return;

  console.log("Order submitted successfully:", order);
}

onMounted(() => {
  orderStore.fetchProducts();
});
</script>

<style scoped>
.item-caption {
  background-color: #2a2a2a;
  border-top-left-radius: 4px;
  border-top-right-radius: 4px;
  height: 56px;
  line-height: 24px;
  padding-top: 15px;
  padding-left: 10px;
}
</style>
