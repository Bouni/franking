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
    <v-col cols="12" lg="2" class="d-none d-lg-block"> </v-col>
    <v-col cols="12" lg="8">
      <v-card class="pa-5">
        <v-form ref="form" v-model="isFormValid" @submit.prevent="handleSubmit">
          <v-card title="Adress data" variant="outlined" class="pa-4 mb-3">
            <v-row density="compact">
              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.firstname"
                  label="First Name"
                  hint="* Required field"
                  persistent-hint
                  :rules="[rules.required]"
                ></v-text-field>
              </v-col>

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.lastname"
                  label="Last Name"
                  hint="* Required field"
                  persistent-hint
                  :rules="[rules.required]"
                ></v-text-field>
              </v-col>

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.email"
                  label="Email Address"
                  hint="* Required field"
                  persistent-hint
                  :rules="[rules.required, rules.email]"
                ></v-text-field>
              </v-col>

              <v-col cols="12" lg="6"> </v-col>

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.address"
                  label="Address"
                  hint="* Required field"
                  persistent-hint
                  :rules="[rules.required]"
                ></v-text-field>
              </v-col>

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.city"
                  label="City"
                  hint="* Required field"
                  persistent-hint
                  :rules="[rules.required]"
                ></v-text-field>
              </v-col>

              <v-col cols="12" lg="6">
                <v-text-field
                  v-model="order.postalcode"
                  label="Postal code"
                  hint="* Required field"
                  persistent-hint
                  :rules="[rules.required]"
                ></v-text-field>
              </v-col>

              <v-col cols="12" lg="6">
                <v-autocomplete
                  v-model="order.country"
                  :items="countries"
                  item-title="name"
                  item-value="code"
                  label="Select Country"
                  :rules="[rules.required]"
                  hint="* Required field"
                  persistent-hint
                  clearable
                >
                  <template #item="{ props, item }">
                    <v-list-item v-bind="props" :title="item.name">
                      <template #prepend>
                        <span
                          class="text-h6 mr-2"
                          :class="`fi fi-${item.code.toLowerCase()}`"
                          style="border-radius: 2px"
                        ></span>
                      </template>
                    </v-list-item>
                  </template>
                  <template #selection="{ item }">
                    <span
                      class="text-h6 mr-2"
                      :class="`fi fi-${order.country.toLowerCase()}`"
                      style="border-radius: 2px"
                    ></span>
                    <span>{{ item.name }}</span>
                  </template>
                </v-autocomplete>
              </v-col>
            </v-row>
          </v-card>

          <v-card title="Items" variant="outlined" class="pa-4">
            <v-row
              v-for="item in order.items"
              key="item.article_number"
              density="compact"
            >
              <v-col cols="12" sm="6" lg="6">
                <div class="item-caption">{{ item.name }}</div>
              </v-col>
              <v-col cols="12" sm="2" lg="2">
                <div class="item-caption">{{ item.price.toFixed(2) }}€</div>
              </v-col>
              <v-col cols="12" sm="2" lg="2">
                <div class="item-caption">
                  {{ (item.quantity * item.price).toFixed(2) }}€
                </div>
              </v-col>
              <v-col cols="12" sm="2" lg="2">
                <v-text-field
                  v-model="item.quantity"
                  label="Quantity"
                  type="number"
                ></v-text-field>
              </v-col>
            </v-row>
            <v-row density="compact">
              <v-col cols="12" sm="6" lg="6">
                <div class="item-caption">Shipping</div>
              </v-col>
              <v-col cols="12" sm="2" lg="2"> </v-col>
              <v-col cols="12" sm="2" lg="2">
                <div class="item-caption">{{ shipping.toFixed(2) }}€</div>
              </v-col>
              <v-col cols="12" sm="2" lg="2"> </v-col>
            </v-row>
            <v-row density="compact">
              <v-col cols="12" sm="6" lg="6">
                <div class="item-caption">Sum</div>
              </v-col>
              <v-col cols="12" sm="2" lg="2"> </v-col>
              <v-col cols="12" sm="2" lg="2">
                <div class="item-caption">{{ grandTotal.toFixed(2) }}€</div>
              </v-col>
              <v-col cols="12" sm="2" lg="2"> </v-col>
            </v-row>
          </v-card>

          <v-row density="compact">
            <v-col cols="12" class="text-center">
              <v-btn type="submit" color="primary" class="mt-4">
                Submit Order
              </v-btn>
            </v-col>
          </v-row>
        </v-form>
      </v-card>
    </v-col>
    <v-col cols="12" lg="2" class="d-none d-lg-block"> </v-col>
  </v-row>
</template>

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

<script setup lang="ts">
import { ref, computed } from "vue";

const countries = [
  { name: "Afghanistan", code: "AF" },
  { name: "Albania", code: "AL" },
  { name: "Algeria", code: "DZ" },
  { name: "Andorra", code: "AD" },
  { name: "Angola", code: "AO" },
  { name: "Antigua and Barbuda", code: "AG" },
  { name: "Argentina", code: "AR" },
  { name: "Armenia", code: "AM" },
  { name: "Australia", code: "AU" },
  { name: "Austria", code: "AT" },
  { name: "Azerbaijan", code: "AZ" },
  { name: "Bahamas", code: "BS" },
  { name: "Bahrain", code: "BH" },
  { name: "Bangladesh", code: "BD" },
  { name: "Barbados", code: "BB" },
  { name: "Belarus", code: "BY" },
  { name: "Belgium", code: "BE" },
  { name: "Belize", code: "BZ" },
  { name: "Benin", code: "BJ" },
  { name: "Bhutan", code: "BT" },
  { name: "Bolivia", code: "BO" },
  { name: "Bosnia and Herzegovina", code: "BA" },
  { name: "Botswana", code: "BW" },
  { name: "Brazil", code: "BR" },
  { name: "Brunei", code: "BN" },
  { name: "Bulgaria", code: "BG" },
  { name: "Burkina Faso", code: "BF" },
  { name: "Burundi", code: "BI" },
  { name: "Cabo Verde", code: "CV" },
  { name: "Cambodia", code: "KH" },
  { name: "Cameroon", code: "CM" },
  { name: "Canada", code: "CA" },
  { name: "Central African Republic", code: "CF" },
  { name: "Chad", code: "TD" },
  { name: "Chile", code: "CL" },
  { name: "China", code: "CN" },
  { name: "Colombia", code: "CO" },
  { name: "Comoros", code: "KM" },
  { name: "Congo", code: "CG" },
  { name: "Costa Rica", code: "CR" },
  { name: "Croatia", code: "HR" },
  { name: "Cuba", code: "CU" },
  { name: "Cyprus", code: "CY" },
  { name: "Czech Republic", code: "CZ" },
  { name: "Denmark", code: "DK" },
  { name: "Djibouti", code: "DJ" },
  { name: "Dominica", code: "DM" },
  { name: "Dominican Republic", code: "DO" },
  { name: "Ecuador", code: "EC" },
  { name: "Egypt", code: "EG" },
  { name: "El Salvador", code: "SV" },
  { name: "Equatorial Guinea", code: "GQ" },
  { name: "Eritrea", code: "ER" },
  { name: "Estonia", code: "EE" },
  { name: "Eswatini", code: "SZ" },
  { name: "Ethiopia", code: "ET" },
  { name: "Fiji", code: "FJ" },
  { name: "Finland", code: "FI" },
  { name: "France", code: "FR" },
  { name: "Gabon", code: "GA" },
  { name: "Gambia", code: "GM" },
  { name: "Georgia", code: "GE" },
  { name: "Germany", code: "DE" },
  { name: "Ghana", code: "GH" },
  { name: "Greece", code: "GR" },
  { name: "Grenada", code: "GD" },
  { name: "Guatemala", code: "GT" },
  { name: "Guinea", code: "GN" },
  { name: "Guinea-Bissau", code: "GW" },
  { name: "Guyana", code: "GY" },
  { name: "Haiti", code: "HT" },
  { name: "Honduras", code: "HN" },
  { name: "Hungary", code: "HU" },
  { name: "Iceland", code: "IS" },
  { name: "India", code: "IN" },
  { name: "Indonesia", code: "ID" },
  { name: "Iran", code: "IR" },
  { name: "Iraq", code: "IQ" },
  { name: "Ireland", code: "IE" },
  { name: "Israel", code: "IL" },
  { name: "Italy", code: "IT" },
  { name: "Jamaica", code: "JM" },
  { name: "Japan", code: "JP" },
  { name: "Jordan", code: "JO" },
  { name: "Kazakhstan", code: "KZ" },
  { name: "Kenya", code: "KE" },
  { name: "Kiribati", code: "KI" },
  { name: "Kuwait", code: "KW" },
  { name: "Kyrgyzstan", code: "KG" },
  { name: "Laos", code: "LA" },
  { name: "Latvia", code: "LV" },
  { name: "Lebanon", code: "LB" },
  { name: "Lesotho", code: "LS" },
  { name: "Liberia", code: "LR" },
  { name: "Libya", code: "LY" },
  { name: "Liechtenstein", code: "LI" },
  { name: "Lithuania", code: "LT" },
  { name: "Luxembourg", code: "LU" },
  { name: "Madagascar", code: "MG" },
  { name: "Malawi", code: "MW" },
  { name: "Malaysia", code: "MY" },
  { name: "Maldives", code: "MV" },
  { name: "Mali", code: "ML" },
  { name: "Malta", code: "MT" },
  { name: "Marshall Islands", code: "MH" },
  { name: "Mauritania", code: "MR" },
  { name: "Mauritius", code: "MU" },
  { name: "Mexico", code: "MX" },
  { name: "Micronesia", code: "FM" },
  { name: "Moldova", code: "MD" },
  { name: "Monaco", code: "MC" },
  { name: "Mongolia", code: "MN" },
  { name: "Montenegro", code: "ME" },
  { name: "Morocco", code: "MA" },
  { name: "Mozambique", code: "MZ" },
  { name: "Myanmar", code: "MM" },
  { name: "Namibia", code: "NA" },
  { name: "Nauru", code: "NR" },
  { name: "Nepal", code: "NP" },
  { name: "Netherlands", code: "NL" },
  { name: "New Zealand", code: "NZ" },
  { name: "Nicaragua", code: "NI" },
  { name: "Niger", code: "NE" },
  { name: "Nigeria", code: "NG" },
  { name: "North Korea", code: "KP" },
  { name: "North Macedonia", code: "MK" },
  { name: "Norway", code: "NO" },
  { name: "Oman", code: "OM" },
  { name: "Pakistan", code: "PK" },
  { name: "Palau", code: "PW" },
  { name: "Palestine", code: "PS" },
  { name: "Panama", code: "PA" },
  { name: "Papua New Guinea", code: "PG" },
  { name: "Paraguay", code: "PY" },
  { name: "Peru", code: "PE" },
  { name: "Philippines", code: "PH" },
  { name: "Poland", code: "PL" },
  { name: "Portugal", code: "PT" },
  { name: "Qatar", code: "QA" },
  { name: "Romania", code: "RO" },
  { name: "Russia", code: "RU" },
  { name: "Rwanda", code: "RW" },
  { name: "Saint Kitts and Nevis", code: "KN" },
  { name: "Saint Lucia", code: "LC" },
  { name: "Saint Vincent and the Grenadines", code: "VC" },
  { name: "Samoa", code: "WS" },
  { name: "San Marino", code: "SM" },
  { name: "Sao Tome and Principe", code: "ST" },
  { name: "Saudi Arabia", code: "SA" },
  { name: "Senegal", code: "SN" },
  { name: "Serbia", code: "RS" },
  { name: "Seychelles", code: "SC" },
  { name: "Sierra Leone", code: "SL" },
  { name: "Singapore", code: "SG" },
  { name: "Slovakia", code: "SK" },
  { name: "Slovenia", code: "SI" },
  { name: "Solomon Islands", code: "SB" },
  { name: "Somalia", code: "SO" },
  { name: "South Africa", code: "ZA" },
  { name: "South Korea", code: "KR" },
  { name: "South Sudan", code: "SS" },
  { name: "Spain", code: "ES" },
  { name: "Sri Lanka", code: "LK" },
  { name: "Sudan", code: "SD" },
  { name: "Suriname", code: "SR" },
  { name: "Sweden", code: "SE" },
  { name: "Switzerland", code: "CH" },
  { name: "Syria", code: "SY" },
  { name: "Taiwan", code: "TW" },
  { name: "Tajikistan", code: "TJ" },
  { name: "Tanzania", code: "TZ" },
  { name: "Thailand", code: "TH" },
  { name: "Timor-Leste", code: "TL" },
  { name: "Togo", code: "TG" },
  { name: "Tonga", code: "TO" },
  { name: "Trinidad and Tobago", code: "TT" },
  { name: "Tunisia", code: "TN" },
  { name: "Turkey", code: "TR" },
  { name: "Turkmenistan", code: "TM" },
  { name: "Tuvalu", code: "TV" },
  { name: "Uganda", code: "UG" },
  { name: "Ukraine", code: "UA" },
  { name: "United Arab Emirates", code: "AE" },
  { name: "United Kingdom", code: "GB" },
  { name: "United States", code: "US" },
  { name: "Uruguay", code: "UY" },
  { name: "Uzbekistan", code: "UZ" },
  { name: "Vanuatu", code: "VU" },
  { name: "Vatican City", code: "VA" },
  { name: "Venezuela", code: "VE" },
  { name: "Vietnam", code: "VN" },
  { name: "Yemen", code: "YE" },
  { name: "Zambia", code: "ZM" },
  { name: "Zimbabwe", code: "ZW" },
];

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

const shipping = computed(() => {
  if (order.value.country == "") {
    return 0;
  } else if (order.value.country == "DE") {
    return 1.8;
  } else {
    return 3.3;
  }
});
// Calculate grand total including shipping
const grandTotal = computed(() => {
  return subtotal.value + shipping.value;
});

// Validation rules array of functions returning true or an error message string
const rules = {
  required: (val: unknown) => !!val || "This field is required.",
  email: (val: string) =>
    /.+@.+\..+/.test(val) || "Must be a valid email address.",
  minQuantity: (val: number) => val >= 1 || "Quantity must be at least 1.",
};

type FormInstance = {
  validate: () => Promise<{ valid: boolean }>;
};

const handleSubmit = async () => {
  const formRef = form.value as FormInstance | null;
  const { valid } = (await formRef?.validate()) ?? { valid: false };

  if (!valid) return;

  console.log("Order submitted successfully:", order);
};
</script>
