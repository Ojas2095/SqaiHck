# data_loader.py
import pandas as pd
import os
from datasets import load_dataset
from huggingface_hub import login
from typing import Dict, List, Optional
import re

class AyurvedaDataLoader:
    """
    A class to load and process data from the local AyurGenixAI_Dataset.xlsx
    and the Hugging Face BhashaBench-Ayur dataset.
    """
    def __init__(self, excel_path: str = "Ayurveda Dataset\AyurGenixAI_Dataset.xlsx", hf_token: Optional[str] = None):
        self.excel_path = excel_path
        self.hf_token = hf_token
        self.local_df = None
        self.hf_dataset = None
        self.hf_dataset_en = None
        self.hf_dataset_hi = None

    def load_local_excel(self) -> pd.DataFrame:
        """Loads the local Excel file and performs basic cleaning."""
        # Check if file exists
        if not os.path.exists(self.excel_path):
            # Try alternative names
            alternatives = [
                "AyurGenixAI_Dataset.xlsx",
                "ayurgenixai_dataset.xlsx",
                "AyurGenixAI_Dataset.XLSX",
                "AyurGenixAI Dataset.xlsx",
                "ayurgenixai.xlsx",
                "AyurGenixAI.xlsx"
            ]
            found = False
            for alt in alternatives:
                if os.path.exists(alt):
                    self.excel_path = alt
                    found = True
                    print(f"âœ… Found Excel file: {alt}")
                    break
            
            if not found:
                print(f"âš ï¸  Warning: Excel file not found. Looked for: {self.excel_path}")
                print("   Please make sure 'AyurGenixAI_Dataset.xlsx' is in the current directory.")
                return pd.DataFrame()

        try:
            # Try to load with the specific sheet name
            try:
                df = pd.read_excel(self.excel_path, sheet_name="AyurGenixAI_Dataset", header=1)
            except:
                # If sheet name fails, try loading the first sheet
                df = pd.read_excel(self.excel_path, header=1)
            
            print(f"âœ… Loaded {len(df)} rows from local Excel file.")
            print(f"   Columns: {list(df.columns)[:10]}...")
            
            # Clean column names
            df.columns = [str(col).strip() for col in df.columns]
            
            self.local_df = df
            return df
        except Exception as e:
            print(f"âŒ Error loading local Excel file: {e}")
            return pd.DataFrame()

    def load_hf_dataset(self, max_rows: Optional[int] = None) -> Dict:
        """
        Loads the BhashaBench-Ayur dataset from Hugging Face in BOTH English and Hindi.
        
        Args:
            max_rows: Maximum rows to load. If None, loads ALL rows.
        """
        if self.hf_token:
            try:
                login(token=self.hf_token)
                print("âœ… Hugging Face login successful")
            except Exception as e:
                print(f"âš ï¸  HF Login error: {e}")

        result = {"english": pd.DataFrame(), "hindi": pd.DataFrame(), "combined": pd.DataFrame()}
        total_loaded = 0
        
        # Load English dataset
        try:
            print(f"ðŸ”½ Loading BhashaBench-Ayur dataset for English...")
            dataset_en = load_dataset("bharatgenai/BhashaBench-Ayur", data_dir="English", split="test", token=self.hf_token)
            df_en = dataset_en.to_pandas()
            
            if max_rows is not None:
                df_en = df_en.head(max_rows)
                print(f"âœ… Loaded {len(df_en)} English questions (limited to {max_rows})")
            else:
                print(f"âœ… Loaded ALL {len(df_en)} English questions")
            
            result["english"] = df_en
            total_loaded += len(df_en)
        except Exception as e:
            print(f"âŒ Error loading English HF dataset: {e}")
            print("   Make sure you have accepted the terms for 'bharatgenai/BhashaBench-Ayur'.")
            print("   Visit: https://huggingface.co/datasets/bharatgenai/BhashaBench-Ayur")
        
        # Load Hindi dataset
        try:
            print(f"ðŸ”½ Loading BhashaBench-Ayur dataset for Hindi...")
            dataset_hi = load_dataset("bharatgenai/BhashaBench-Ayur", data_dir="Hindi", split="test", token=self.hf_token)
            df_hi = dataset_hi.to_pandas()
            
            if max_rows is not None:
                df_hi = df_hi.head(max_rows)
                print(f"âœ… Loaded {len(df_hi)} Hindi questions (limited to {max_rows})")
            else:
                print(f"âœ… Loaded ALL {len(df_hi)} Hindi questions")
            
            result["hindi"] = df_hi
            total_loaded += len(df_hi)
        except Exception as e:
            print(f"âŒ Error loading Hindi HF dataset: {e}")
            print("   Make sure you have accepted the terms for 'bharatgenai/BhashaBench-Ayur'.")
            print("   Visit: https://huggingface.co/datasets/bharatgenai/BhashaBench-Ayur")
        
        # Combine both
        combined = pd.concat([result["english"], result["hindi"]], ignore_index=True)
        result["combined"] = combined
        self.hf_dataset = combined
        self.hf_dataset_en = result["english"]
        self.hf_dataset_hi = result["hindi"]
        
        print(f"âœ… Combined dataset: {len(combined)} total questions")
        print(f"   - English: {len(result['english'])}")
        print(f"   - Hindi: {len(result['hindi'])}")
        print(f"   - Total loaded: {total_loaded}")
        
        return result

    def process_for_rag(self) -> List[str]:
        """
        Processes the loaded data into text chunks suitable for your RAG system.
        """
        chunks = []
        
        # Process local Excel data
        if self.local_df is not None and not self.local_df.empty:
            print("ðŸ”¨ Creating RAG chunks from local dataset...")
            
            # Get the actual column names from the Excel file
            columns = self.local_df.columns.tolist()
            print(f"   Columns found: {columns[:10]}...")
            
            for idx, row in self.local_df.iterrows():
                # Safely get values from each column with fallbacks
                disease = self._safe_get(row, 'Disease', 'disease', 'N/A')
                hindi_name = self._safe_get(row, 'Hindi Name', 'hindi_name', 'N/A')
                marathi_name = self._safe_get(row, 'Marathi Name', 'marathi_name', 'N/A')
                symptoms = self._safe_get(row, 'Symptoms', 'symptoms', 'N/A')
                diagnosis = self._safe_get(row, 'Diagnosis & Tests', 'diagnosis_tests', 'N/A')
                severity = self._safe_get(row, 'Symptom Severity', 'severity', 'N/A')
                duration = self._safe_get(row, 'Duration of Treatment', 'duration', 'N/A')
                medical_history = self._safe_get(row, 'Medical History', 'medical_history', 'N/A')
                medications = self._safe_get(row, 'Current Medications', 'medications', 'N/A')
                risk_factors = self._safe_get(row, 'Risk Factors', 'risk_factors', 'N/A')
                environmental = self._safe_get(row, 'Environmental Factors', 'environmental', 'N/A')
                sleep = self._safe_get(row, 'Sleep Patterns', 'sleep', 'N/A')
                stress = self._safe_get(row, 'Stress Levels', 'stress', 'N/A')
                physical_activity = self._safe_get(row, 'Physical Activity Levels', 'physical_activity', 'N/A')
                family_history = self._safe_get(row, 'Family History', 'family_history', 'N/A')
                dietary_habits = self._safe_get(row, 'Dietary Habits', 'dietary_habits', 'N/A')
                allergies = self._safe_get(row, 'Allergies (Food/Env)', 'allergies', 'N/A')
                seasonal = self._safe_get(row, 'Seasonal Variation', 'seasonal', 'N/A')
                age_group = self._safe_get(row, 'Age Group', 'age_group', 'N/A')
                gender = self._safe_get(row, 'Gender', 'gender', 'N/A')
                occupation = self._safe_get(row, 'Occupation and Lifestyle', 'occupation', 'N/A')
                cultural = self._safe_get(row, 'Cultural Preferences', 'cultural', 'N/A')
                herbal_remedies = self._safe_get(row, 'Herbal/Alternative Remedies', 'herbal_remedies', 'N/A')
                ayurvedic_herbs = self._safe_get(row, 'Ayurvedic Herbs', 'ayurvedic_herbs', 'N/A')
                formulation = self._safe_get(row, 'Formulation', 'formulation', 'N/A')
                doshas = self._safe_get(row, 'Doshas', 'doshas', 'N/A')
                prakriti = self._safe_get(row, 'Constitution/Prakriti', 'prakriti', 'N/A')
                diet_recommendations = self._safe_get(row, 'Diet and Lifestyle Recommendations', 'diet_recommendations', 'N/A')
                yoga = self._safe_get(row, 'Yoga & Physical Therapy', 'yoga', 'N/A')
                medical_intervention = self._safe_get(row, 'Medical Intervention', 'medical_intervention', 'N/A')
                prevention = self._safe_get(row, 'Prevention', 'prevention', 'N/A')
                prognosis = self._safe_get(row, 'Prognosis', 'prognosis', 'N/A')
                complications = self._safe_get(row, 'Complications', 'complications', 'N/A')
                patient_recs = self._safe_get(row, 'Patient Recommendations', 'patient_recs', 'N/A')
                
                # Skip if no disease name
                if disease == 'N/A' or not disease:
                    continue
                
                # Build the chunk
                chunk = f"""
                Disease: {disease}
                Hindi Name: {hindi_name}
                Marathi Name: {marathi_name}
                Symptoms: {symptoms}
                Diagnosis & Tests: {diagnosis}
                Symptom Severity: {severity}
                Duration of Treatment: {duration}
                Medical History: {medical_history}
                Current Medications: {medications}
                Risk Factors: {risk_factors}
                Environmental Factors: {environmental}
                Sleep Patterns: {sleep}
                Stress Levels: {stress}
                Physical Activity: {physical_activity}
                Family History: {family_history}
                Dietary Habits: {dietary_habits}
                Allergies: {allergies}
                Seasonal Variation: {seasonal}
                Age Group: {age_group}
                Gender: {gender}
                Occupation: {occupation}
                Cultural Preferences: {cultural}
                Herbal/Alternative Remedies: {herbal_remedies}
                Ayurvedic Herbs: {ayurvedic_herbs}
                Formulation: {formulation}
                Doshas: {doshas}
                Constitution/Prakriti: {prakriti}
                Diet and Lifestyle Recommendations: {diet_recommendations}
                Yoga & Physical Therapy: {yoga}
                Medical Intervention: {medical_intervention}
                Prevention: {prevention}
                Prognosis: {prognosis}
                Complications: {complications}
                Patient Recommendations: {patient_recs}
                """
                chunks.append(chunk.strip())

        # Process English HF dataset
        if hasattr(self, 'hf_dataset_en') and self.hf_dataset_en is not None and not self.hf_dataset_en.empty:
            print("ðŸ”¨ Creating RAG chunks from English HF dataset...")
            for _, row in self.hf_dataset_en.iterrows():
                question = str(row.get('question', 'N/A')).strip()
                answer = str(row.get('answer', 'N/A')).strip()
                subject = str(row.get('subject', 'N/A')).strip()
                difficulty = str(row.get('difficulty', 'N/A')).strip()
                question_type = str(row.get('question_type', 'N/A')).strip()
                
                chunk = f"""
                Ayurveda Question (English): {question}
                Correct Answer: {answer}
                Subject: {subject}
                Difficulty: {difficulty}
                Question Type: {question_type}
                """
                chunks.append(chunk.strip())
        
        # Process Hindi HF dataset
        if hasattr(self, 'hf_dataset_hi') and self.hf_dataset_hi is not None and not self.hf_dataset_hi.empty:
            print("ðŸ”¨ Creating RAG chunks from Hindi HF dataset...")
            for _, row in self.hf_dataset_hi.iterrows():
                question = str(row.get('question', 'N/A')).strip()
                answer = str(row.get('answer', 'N/A')).strip()
                subject = str(row.get('subject', 'N/A')).strip()
                difficulty = str(row.get('difficulty', 'N/A')).strip()
                question_type = str(row.get('question_type', 'N/A')).strip()
                
                chunk = f"""
                Ayurveda Question (Hindi): {question}
                Correct Answer: {answer}
                Subject: {subject}
                Difficulty: {difficulty}
                Question Type: {question_type}
                """
                chunks.append(chunk.strip())

        print(f"âœ… Created {len(chunks)} RAG chunks from combined datasets.")
        print(f"   - Local Excel: {len(self.local_df) if self.local_df is not None else 0} rows")
        print(f"   - English HF: {len(self.hf_dataset_en) if hasattr(self, 'hf_dataset_en') and self.hf_dataset_en is not None else 0} questions")
        print(f"   - Hindi HF: {len(self.hf_dataset_hi) if hasattr(self, 'hf_dataset_hi') and self.hf_dataset_hi is not None else 0} questions")
        return chunks
    
    def _safe_get(self, row, *keys, default='N/A'):
        """Safely get a value from a row using multiple possible column names."""
        for key in keys:
            if key in row and pd.notna(row[key]):
                value = str(row[key]).strip()
                if value and value != 'nan':
                    return value
        return default

    def get_local_dataframe(self) -> pd.DataFrame:
        """Returns the local dataframe."""
        return self.local_df if self.local_df is not None else pd.DataFrame()

    def get_hf_dataframe(self) -> pd.DataFrame:
        """Returns the combined Hugging Face dataframe."""
        return self.hf_dataset if self.hf_dataset is not None else pd.DataFrame()
    
    def get_hf_english_dataframe(self) -> pd.DataFrame:
        """Returns the English Hugging Face dataframe."""
        return self.hf_dataset_en if hasattr(self, 'hf_dataset_en') and self.hf_dataset_en is not None else pd.DataFrame()
    
    def get_hf_hindi_dataframe(self) -> pd.DataFrame:
        """Returns the Hindi Hugging Face dataframe."""
        return self.hf_dataset_hi if hasattr(self, 'hf_dataset_hi') and self.hf_dataset_hi is not None else pd.DataFrame()
