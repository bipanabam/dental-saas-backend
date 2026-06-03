"""
Findings, diagnoses, investigations, and treatment plan descriptions.
"""

DENTAL_PROBLEM_TAXONOMY: dict[str, list[str]] = {
    "Tooth-Related Problems": [
        "Toothache","Dental Caries (Tooth Decay)","Sensitive Teeth","Broken Tooth",
        "Cracked Tooth","Chipped Tooth","Worn Tooth","Discolored Tooth",
        "Mobile (Loose) Tooth","Impacted Tooth","Missing Tooth","Supernumerary Tooth",
        "Attrition","Abrasion","Erosion","Tooth Fracture","Pulp Exposure",
    ],
    "Pulp & Nerve Problems (Endodontic)": [
        "Pulpitis (Reversible / Irreversible)","Pulp Necrosis","Periapical Abscess",
        "Periapical Infection","Root Canal Infection","Failed Root Canal",
        "Internal Resorption","External Resorption",
    ],
    "Gum & Periodontal Problems": [
        "Gingivitis","Periodontitis","Gum Bleeding","Gum Swelling","Gum Recession",
        "Periodontal Pocket","Bone Loss Around Teeth","Tooth Mobility",
        "Bad Breath (Halitosis)","Periodontal Abscess",
    ],
    "Oral Soft Tissue Problems": [
        "Mouth Ulcer","Oral Infection","Oral Candidiasis","Herpes Simplex Infection",
        "Leukoplakia","Oral Lichen Planus","Oral Cancer Suspicion",
        "Burning Mouth Syndrome","Dry Mouth (Xerostomia)","Salivary Gland Disorder",
    ],
    "Jaw & TMJ Problems": [
        "Jaw Pain","TMJ Disorder","Clicking Jaw","Limited Mouth Opening",
        "Jaw Dislocation","Bruxism (Teeth Grinding)","Facial Pain","Muscle Spasm",
    ],
    "Bite & Alignment Problems (Orthodontic)": [
        "Crowded Teeth","Spacing Between Teeth","Overbite","Underbite","Crossbite",
        "Open Bite","Midline Shift","Malocclusion","Protruding Teeth","Impacted Canine",
    ],
    "Prosthetic / Restoration Problems": [
        "Lost Filling","Broken Filling","Crown Failure","Bridge Failure",
        "Loose Denture","Ill-Fitting Denture","Implant Failure","Veneer Damage",
    ],
    "Surgical Conditions": [
        "Impacted Wisdom Tooth","Tooth Infection Requiring Extraction","Dental Cyst",
        "Oral Tumor","Jaw Infection","Facial Swelling","Trauma Injury",
    ],
    "Pediatric Dental Problems": [
        "Early Childhood Caries","Nursing Bottle Caries","Delayed Tooth Eruption",
        "Premature Tooth Loss","Thumb Sucking Habit","Tongue Thrusting","Space Loss",
    ],
    "Cosmetic Complaints": [
        "Yellow Teeth","Stained Teeth","Uneven Smile","Gummy Smile",
        "Uneven Tooth Shape","Smile Dissatisfaction",
    ],
    "Emergency Dental Problems": [
        "Severe Tooth Pain","Dental Trauma","Knocked-Out Tooth (Avulsion)",
        "Tooth Luxation","Facial Infection","Bleeding After Extraction","Swelling with Fever",
    ],
    "General Patient Complaints": [
        "Pain While Chewing","Sensitivity to Hot/Cold","Food Lodgement",
        "Bad Taste in Mouth","Difficulty Biting","Difficulty Opening Mouth",
        "Bleeding Gums While Brushing","Broken Dental Appliance",
    ],
}

DENTAL_DIAGNOSIS_TAXONOMY: dict[str, list[str]] = {
    "Dental Caries Diagnoses": [
        "Dental caries","Deep dental caries","Recurrent caries",
        "Root caries","Rampant caries","Arrested caries",
    ],
    "Pulpal Diseases": [
        "Reversible pulpitis","Irreversible pulpitis","Acute pulpitis",
        "Chronic pulpitis","Pulp necrosis","Hyperplastic pulpitis (pulp polyp)",
    ],
    "Periapical Diseases": [
        "Acute apical periodontitis","Chronic apical periodontitis","Periapical abscess",
        "Periapical granuloma","Radicular cyst",
    ],
    "Periodontal Diagnoses": [
        "Generalized chronic gingivitis","Localized gingivitis","Chronic periodontitis",
        "Aggressive periodontitis","Gingival enlargement","Periodontal abscess",
        "Gingival recession",
    ],
    "Oral Surgery Diagnoses": [
        "Impacted third molar","Pericoronitis","Dry socket (alveolar osteitis)",
        "Cellulitis","Temporomandibular joint disorder (TMD)","Maxillofacial trauma/fracture",
    ],
    "Orthodontic Diagnoses": [
        "Class I malocclusion","Class II malocclusion","Class III malocclusion",
        "Crowding","Spacing/diastema","Crossbite","Open bite","Deep bite",
    ],
    "Prosthodontic Diagnoses": [
        "Partial edentulism","Complete edentulism","Ill-fitting denture",
        "Failed crown/bridge","Attrition-related loss of vertical dimension",
    ],
    "Oral Medicine Diagnoses": [
        "Recurrent aphthous ulcer","Oral submucous fibrosis (OSMF)","Leukoplakia",
        "Oral candidiasis","Lichen planus","Burning mouth syndrome","Xerostomia",
    ],
    "Pediatric Dental Diagnoses": [
        "Early childhood caries","Nursing bottle caries","Pulpally involved primary tooth",
        "Retained deciduous tooth","Fluorosis",
    ],
}

DENTAL_INVESTIGATION_TAXONOMY: dict[str, list[str]] = {
    "Routine Dental Investigations": [
        "Intraoral periapical radiograph (IOPA)","Bitewing radiograph","Occlusal radiograph",
        "Orthopantomogram (OPG)","Cone beam CT (CBCT)","RVG (Radiovisiography)",
    ],
    "Pulp Vitality Tests": [
        "Thermal test - hot test","Thermal test - cold test","Electric pulp test (EPT)",
        "Test cavity","Percussion test","Palpation test",
    ],
    "Periodontal Investigations": [
        "Periodontal probing","Pocket depth measurement","Bleeding on probing",
        "Plaque index","Gingival index","Mobility grading","Furcation assessment",
    ],
    "Investigations for Oral Surgery Cases": [
        "OPG","CBCT for impacted teeth","CT scan for fractures/tumors",
        "Chest X-ray (if medically indicated)","ECG before surgery (if required)",
    ],
    "Orthodontic Investigations": [
        "Cephalometric radiograph","Study models/casts","Photographs",
        "Cephalometric analysis","Space analysis",
    ],
    "Prosthodontic Investigations": [
        "Diagnostic impressions","Jaw relation records","Facebow transfer","Articulator mounting",
    ],
    "Oral Medicine Investigations": [
        "Biopsy","Exfoliative cytology","Toluidine blue staining",
        "Culture and sensitivity test","Salivary analysis",
    ],
    "Hematological Investigations": [
        "Complete blood count (CBC)","Hemoglobin percentage (Hb%)","Bleeding time (BT)",
        "Clotting time (CT)","Blood sugar level","ESR","Platelet count",
    ],
    "Biochemical Investigations": [
        "Random blood sugar (RBS)","Fasting blood sugar (FBS)","HbA1c",
        "Liver function test (LFT)","Kidney function test (KFT)","Serum calcium/phosphorus",
    ],
    "Microbiological Investigations": [
        "Pus culture","Fungal smear","Viral screening","Bacterial sensitivity test",
    ],
}

DENTAL_TREATMENT_TAXONOMY: dict[str, list[str]] = {
    "General Dental Treatment Plans": [
        "Oral prophylaxis (scaling and polishing)","Oral hygiene instructions",
        "Fluoride therapy","Dietary counseling","Regular follow-up",
    ],
    "Restorative Treatment Plans": [
        "Dental filling/restoration","Glass ionomer cement (GIC) restoration",
        "Composite restoration","Amalgam restoration","Inlay/onlay","Veneers",
    ],
    "Endodontic Treatment Plans": [
        "Indirect pulp capping","Direct pulp capping","Pulpotomy","Pulpectomy",
        "Root canal treatment (RCT)","Retreatment RCT","Apicoectomy",
    ],
    "Periodontal Treatment Plans": [
        "Scaling and root planing","Curettage","Flap surgery","Gingivectomy",
        "Splinting of mobile teeth","Periodontal maintenance therapy",
    ],
    "Oral Surgery Treatment Plans": [
        "Tooth extraction","Surgical extraction","Impaction removal",
        "Incision and drainage","Biopsy","Management of fractures","TMJ therapy",
    ],
    "Prosthodontic Treatment Plans": [
        "Removable partial denture","Complete denture","Fixed partial denture (bridge)",
        "Crown placement","Implant-supported prosthesis","Denture relining/rebasing",
    ],
    "Orthodontic Treatment Plans": [
        "Removable appliance therapy","Fixed orthodontic treatment (braces)",
        "Space maintainer","Habit-breaking appliance","Retainers after treatment",
    ],
    "Pediatric Dental Treatment Plans": [
        "Preventive resin restoration","Pit and fissure sealants","Stainless steel crown",
        "Space maintainer","Fluoride application","Pulp therapy for primary teeth",
    ],
    "Oral Medicine Treatment Plans": [
        "Topical medications","Antifungal therapy","Steroid therapy",
        "Habit cessation counseling","Surgical excision of lesion",
    ],
}