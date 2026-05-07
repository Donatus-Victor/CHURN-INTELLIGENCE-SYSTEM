# CHURN-INTELLIGENCE-SYSTEM

🚀 Telecom Churn & Segment Predictor: This is an End-to-End Customer Intelligence Dashboard designed to reduce revenue loss for telecommunication companies. By combining Supervised Learning (XGBoost) with Unsupervised Learning (K-Means), the system doesn't just predict who will leave—it explains why they are leaving and how to keep them.

📈 The Business Problem: Customer churn is expensive. Acquiring a new customer costs 5x more than retaining an existing one. This project provides managers with a tool to identify high-risk customers before they leave and categorizes them into behavioural segments for targeted marketing.

🛠️ Technical WorkflowData Engineering: Processed the IBM Telco dataset, handled class imbalance (2.75:1) using scale_pos_weight, and engineered features to achieve a 79% Recall score.Predictive Modelling: Optimized an XGBoost Classifier to identify churn risk with a minimal 1.45% generalization gap between training and testing.Customer Segmentation: Implemented K-Means Clustering (validated via the Elbow Method) to group the 7,043 customers into three distinct personas.Deployment: Developed a custom Streamlit Dashboard that serves as a real-time CRM interface.

📋 How It Works: The "Manager's View"The dashboard is designed for a non-technical manager to use in daily operations:1. Search & Tracking. Instead of manually entering data, the manager uses the Customer Lookup feature. Unique Identifier: Enter an 11-digit Nigerian phone number (e.g., starting with 080, 070).Instant Retrieval: The app queries the customer_lookup_database.csv to pull the specific customer’s tenure, contract type, and service usage.

Real-Time Risk Assessment. Once a customer is found, the system runs their data through the XGBoost model: Probability Score: Displays the exact percentage chance of churn (e.g., "84.2% Risk").Visual Verdict: High-risk customers are flagged with a red warning for immediate attention.

Behavioural Segmentation. Simultaneously, the K-Means model identifies the customer's cluster: Cluster 1 (At-Risk Starters): Usually new, month-to-month users on high-speed fiber but with no support services. Cluster 2 (Loyal Power Users): Long-term users with multiple service add-ons.Cluster 0 (Traditionalists): Low-tech users with basic services.

Actionable StrategyThe app generates a Strategic Advice note based on the cluster. For example, if a high-risk customer is in Cluster 1, the app suggests: "Offer a 20% discount on an annual contract to increase stickiness."
