# 9. Dashboard Sample Test Scenarios

Below are **9 fully structured scenarios** covering all execution modes: DOM-only, Real-time URL, Vision-only, and Hybrid.

---

## Scenario 1 — Dummy DOM: ID Changed

**Mode:** DOM-only  
**Purpose:** Recover after ID change  

**Page URL:**  
```
https://dummy.local/login
```

**Expected Text:**  
```
Login
```

**Old Locator:**  
```
 //button[@id='login_old']
```

**Old Locator Type:**  
```
XPath
```

**Page HTML Snapshot:**

```html
<!doctype html>
<html>
<body>
<form>
<button id="login_new" class="btn primary">Login</button>
</form>
</body>
</html>
```

**Expected Result:**

- Strategy → `attribute_text_similarity`  
- Score → High (greater than threshold)

---

## Scenario 2 — Dummy DOM: Button to Anchor Migration

**Mode:** DOM-only  
**Purpose:** Recover tag migration  

**Page URL:**  
```
https://dummy.local/details
```

**Expected Text:**  
```
View details
```

**Old Locator:**  
```
 //button[@id='view_details']
```

**Page HTML Snapshot:**

```html
<!doctype html>
<html>
<body>
<div class="card">
<a id="view_details_link" class="btn primary">View details</a>
</div>
</body>
</html>
```

**Expected Result:**

- Strategy → `attribute_text_similarity`  
- Returns `<a>` element  

---

## Scenario 3 — Dummy DOM: Text Changed

**Mode:** DOM-only  

**Expected Text:**  
```
Sign in
```

**Old Locator:**  
```
 //button[@id='login_btn']
```

**Page HTML Snapshot:**

```html
<button id="login_btn" class="btn primary">Sign in</button>
```

**Expected Result:**

- Strategy → `attribute_text_similarity` or `xpath_original`

---

## Scenario 4 — Live URL: Heroku Login

**Mode:** Real-time URL  

**Page URL:**  
```
https://the-internet.herokuapp.com/login
```

**Expected Text:**  
```
Login
```

**Old Locator:**  
```
 //button[@id='login_old']
```

**HTML Snapshot:**  
Leave empty  

**Expected Result:**

- Strategy → `attribute_text_similarity`  
- DOM fetched dynamically  

---

## Scenario 5 — Live URL: Forgot Password

**Mode:** Real-time URL  

**Page URL:**  
```
https://the-internet.herokuapp.com/forgot_password
```

**Expected Text:**  
```
Retrieve password
```

**Old Locator:**  
```
Broken XPath
```

**Expected Result:**

- Strategy → `attribute_text_similarity`

---

## Scenario 6 — Vision-Only: Login Button

**Mode:** Vision-only  

**Page URL:**  
```
dummy
```

**Screenshot Path:**  
```
data/raw/screenshots/full/login_v1.png
```

**Template Path:**  
```
data/raw/screenshots/templates/login_button.png
```

**HTML Snapshot:**  
Leave empty  

**Expected Result:**

- Strategy → `vision_template_match`  
- Vision match score displayed  

---

## Scenario 7 — Hybrid Mode: Vision + DOM

**Mode:** Hybrid  

**Inputs Provided:**

- Screenshot  
- Template image  
- HTML snapshot  
- Broken old locator  

**Expected Result:**

- Vision detects region  
- DOM generates XPath or CSS selector  

---

## Scenario 8 — Low Confidence Case

**Mode:** DOM-only  

**Expected Text:**  
```
Register
```

**Actual Button Text:**  
```
Login
```

**Expected Result:**

- Low similarity  
- Score less than threshold  
- `element_candidate` → null  

---

## Scenario 9 — Multiple Similar Buttons

**Mode:** DOM-only  

**Page HTML Snapshot:**

```html
<button class="btn">Submit</button>
<button class="btn primary">Submit</button>
```

**Expected Text:**  
```
Submit
```

**Expected Result:**

- Multiple candidates generated  
- ML selects highest confidence  
- Score reflects discrimination strength  

---