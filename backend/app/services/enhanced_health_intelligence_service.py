"""
Enhanced Health Intelligence Service

This service provides advanced health assessment capabilities including:
- Pet-specific health risk analysis
- Symptom pattern recognition
- Medication interaction checking
- Preventive care recommendations
- Health trend analysis with scoring
- Emergency triage with context
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from enum import Enum

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.care_record import CareRecord, Document, KnowledgeBase
from app.services.ai_service import AIService
from app import db

logger = logging.getLogger(__name__)

class HealthRiskLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

class HealthAlert(BaseModel):
    alert_type: str = Field(description="Type of health alert")
    priority: int = Field(description="Priority level 1-5", ge=1, le=5)
    message: str = Field(description="Alert message")
    recommended_action: str = Field(description="Recommended action")
    timeframe: str = Field(description="Timeframe for action")

class PetHealthProfile(BaseModel):
    pet_name: str
    breed: Optional[str] = None
    age_months: Optional[int] = None
    weight_kg: Optional[float] = None
    risk_factors: List[str] = Field(default_factory=list)
    chronic_conditions: List[str] = Field(default_factory=list)
    current_medications: List[str] = Field(default_factory=list)
    vaccination_status: Dict[str, Any] = Field(default_factory=dict)
    last_checkup: Optional[str] = None

class HealthAssessment(BaseModel):
    pet_name: str
    overall_risk: HealthRiskLevel
    risk_score: float = Field(description="Risk score 0-100", ge=0, le=100)
    key_concerns: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    alerts: List[HealthAlert] = Field(default_factory=list)
    next_checkup_recommended: Optional[str] = None
    preventive_care_due: List[str] = Field(default_factory=list)

class EnhancedHealthIntelligenceService:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
        self.ai_service = AIService()
        
        # Health knowledge base
        self.breed_risk_factors = self._load_breed_risk_factors()
        self.vaccination_schedules = self._load_vaccination_schedules()
        self.medication_interactions = self._load_medication_interactions()
    
    async def comprehensive_health_assessment(self, user_id: int, pet_name: str = None) -> HealthAssessment:
        """Perform comprehensive health assessment for a pet"""
        try:
            # Get pet health profile
            profile = await self._build_pet_health_profile(user_id, pet_name)
            
            # Analyze health risks
            risk_analysis = await self._analyze_health_risks(profile)
            
            # Check for alerts
            alerts = await self._check_health_alerts(profile)
            
            # Generate recommendations
            recommendations = await self._generate_health_recommendations(profile, risk_analysis)
            
            # Create assessment
            assessment = HealthAssessment(
                pet_name=profile.pet_name,
                overall_risk=risk_analysis['overall_risk'],
                risk_score=risk_analysis['risk_score'],
                key_concerns=risk_analysis['concerns'],
                recommendations=recommendations,
                alerts=alerts,
                next_checkup_recommended=self._calculate_next_checkup(profile),
                preventive_care_due=self._check_preventive_care_due(profile)
            )
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error in comprehensive health assessment: {str(e)}")
            return HealthAssessment(
                pet_name=pet_name or "Unknown",
                overall_risk=HealthRiskLevel.MODERATE,
                risk_score=50.0,
                key_concerns=["Unable to complete assessment"],
                recommendations=["Please try again or consult your veterinarian"],
                alerts=[]
            )
    
    async def _build_pet_health_profile(self, user_id: int, pet_name: str = None) -> PetHealthProfile:
        """Build comprehensive pet health profile from existing data"""
        try:
            # Get care records for the pet
            query = CareRecord.query.filter_by(user_id=user_id, is_active=True)
            if pet_name:
                query = query.filter_by(pet_name=pet_name)
            
            care_records = query.order_by(CareRecord.date_occurred.desc()).all()
            
            if not care_records:
                return PetHealthProfile(pet_name=pet_name or "Unknown Pet")
            
            # Extract pet details from most recent record
            latest_record = care_records[0]
            profile = PetHealthProfile(
                pet_name=latest_record.pet_name or pet_name or "Unknown Pet",
                breed=latest_record.pet_breed,
                age_months=latest_record.pet_age,
                weight_kg=latest_record.pet_weight
            )
            
            # Analyze care records for health patterns
            profile = self._analyze_care_records_for_profile(profile, care_records)
            
            return profile
            
        except Exception as e:
            logger.error(f"Error building pet health profile: {str(e)}")
            return PetHealthProfile(pet_name=pet_name or "Unknown Pet")
    
    def _analyze_care_records_for_profile(self, profile: PetHealthProfile, records: List[CareRecord]) -> PetHealthProfile:
        """Extract health insights from care records"""
        try:
            vaccination_records = []
            medication_records = []
            vet_visits = []
            symptoms_history = []
            
            for record in records:
                if record.category == 'vaccination':
                    vaccination_records.append(record)
                elif record.category == 'medication':
                    medication_records.append(record)
                    if record.medications:
                        profile.current_medications.extend(record.medications)
                elif record.category == 'vet_visit':
                    vet_visits.append(record)
                
                # Extract symptoms
                if record.symptoms:
                    symptoms_history.extend(record.symptoms)
                
                # Identify chronic conditions from descriptions
                if record.description:
                    chronic_conditions = self._extract_chronic_conditions(record.description)
                    profile.chronic_conditions.extend(chronic_conditions)
            
            # Update vaccination status
            profile.vaccination_status = self._analyze_vaccination_status(vaccination_records)
            
            # Get last checkup
            if vet_visits:
                profile.last_checkup = vet_visits[0].date_occurred.isoformat()
            
            # Identify risk factors
            profile.risk_factors = self._identify_risk_factors(profile, symptoms_history)
            
            # Remove duplicates
            profile.current_medications = list(set(profile.current_medications))
            profile.chronic_conditions = list(set(profile.chronic_conditions))
            profile.risk_factors = list(set(profile.risk_factors))
            
            return profile
            
        except Exception as e:
            logger.error(f"Error analyzing care records: {str(e)}")
            return profile
    
    async def _analyze_health_risks(self, profile: PetHealthProfile) -> Dict[str, Any]:
        """Analyze health risks based on pet profile"""
        try:
            risk_score = 0.0
            concerns = []
            
            # Age-based risk
            if profile.age_months:
                if profile.age_months < 6:  # Puppy
                    risk_score += 10
                    concerns.append("Young age requires careful monitoring")
                elif profile.age_months > 84:  # Senior (7+ years)
                    risk_score += 20
                    concerns.append("Senior age increases health risks")
            
            # Breed-specific risks
            if profile.breed and profile.breed.lower() in self.breed_risk_factors:
                breed_risks = self.breed_risk_factors[profile.breed.lower()]
                risk_score += len(breed_risks) * 5
                concerns.extend([f"Breed risk: {risk}" for risk in breed_risks])
            
            # Chronic conditions
            risk_score += len(profile.chronic_conditions) * 15
            if profile.chronic_conditions:
                concerns.extend([f"Chronic condition: {condition}" for condition in profile.chronic_conditions])
            
            # Medication interactions
            if len(profile.current_medications) > 1:
                interactions = self._check_medication_interactions(profile.current_medications)
                if interactions:
                    risk_score += len(interactions) * 10
                    concerns.extend([f"Medication interaction: {interaction}" for interaction in interactions])
            
            # Vaccination status
            overdue_vaccines = self._check_overdue_vaccinations(profile)
            if overdue_vaccines:
                risk_score += len(overdue_vaccines) * 8
                concerns.extend([f"Overdue vaccination: {vaccine}" for vaccine in overdue_vaccines])
            
            # Determine overall risk level
            if risk_score >= 70:
                overall_risk = HealthRiskLevel.CRITICAL
            elif risk_score >= 50:
                overall_risk = HealthRiskLevel.HIGH
            elif risk_score >= 25:
                overall_risk = HealthRiskLevel.MODERATE
            else:
                overall_risk = HealthRiskLevel.LOW
            
            return {
                'overall_risk': overall_risk,
                'risk_score': min(risk_score, 100.0),
                'concerns': concerns[:5]  # Limit to top 5 concerns
            }
            
        except Exception as e:
            logger.error(f"Error analyzing health risks: {str(e)}")
            return {
                'overall_risk': HealthRiskLevel.MODERATE,
                'risk_score': 50.0,
                'concerns': ["Unable to assess risk factors"]
            }
    
    async def _check_health_alerts(self, profile: PetHealthProfile) -> List[HealthAlert]:
        """Check for immediate health alerts"""
        alerts = []
        
        try:
            # Check overdue vaccinations
            overdue_vaccines = self._check_overdue_vaccinations(profile)
            for vaccine in overdue_vaccines:
                alerts.append(HealthAlert(
                    alert_type="overdue_vaccination",
                    priority=3,
                    message=f"{vaccine} vaccination is overdue",
                    recommended_action="Schedule vaccination appointment",
                    timeframe="Within 2 weeks"
                ))
            
            # Check medication interactions
            interactions = self._check_medication_interactions(profile.current_medications)
            for interaction in interactions:
                alerts.append(HealthAlert(
                    alert_type="medication_interaction",
                    priority=4,
                    message=f"Potential medication interaction: {interaction}",
                    recommended_action="Consult veterinarian about medications",
                    timeframe="Within 1 week"
                ))
            
            # Check overdue checkup
            if self._is_checkup_overdue(profile):
                alerts.append(HealthAlert(
                    alert_type="overdue_checkup",
                    priority=2,
                    message="Annual checkup is overdue",
                    recommended_action="Schedule routine health examination",
                    timeframe="Within 1 month"
                ))
            
            return alerts[:3]  # Limit to top 3 alerts
            
        except Exception as e:
            logger.error(f"Error checking health alerts: {str(e)}")
            return []
    
    async def _generate_health_recommendations(self, profile: PetHealthProfile, risk_analysis: Dict) -> List[str]:
        """Generate personalized health recommendations"""
        try:
            recommendations = []
            
            # Age-specific recommendations
            if profile.age_months:
                if profile.age_months < 6:
                    recommendations.extend([
                        "Complete puppy vaccination series",
                        "Establish regular feeding schedule",
                        "Begin socialization training"
                    ])
                elif profile.age_months > 84:
                    recommendations.extend([
                        "Schedule bi-annual senior health checkups",
                        "Monitor weight and mobility",
                        "Consider senior-specific nutrition"
                    ])
            
            # Breed-specific recommendations
            if profile.breed and profile.breed.lower() in self.breed_risk_factors:
                breed_recommendations = self._get_breed_specific_recommendations(profile.breed)
                recommendations.extend(breed_recommendations)
            
            # Weight management
            if profile.weight_kg and profile.breed:
                weight_recommendations = self._get_weight_recommendations(profile)
                recommendations.extend(weight_recommendations)
            
            # Risk-based recommendations
            if risk_analysis['overall_risk'] in [HealthRiskLevel.HIGH, HealthRiskLevel.CRITICAL]:
                recommendations.extend([
                    "Schedule immediate veterinary consultation",
                    "Monitor symptoms closely",
                    "Keep emergency vet contact readily available"
                ])
            
            return recommendations[:5]  # Limit to top 5 recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return ["Consult with your veterinarian for personalized care advice"]
    
    def _load_breed_risk_factors(self) -> Dict[str, List[str]]:
        """Load breed-specific risk factors"""
        return {
            'golden retriever': ['hip dysplasia', 'cancer', 'heart disease'],
            'german shepherd': ['hip dysplasia', 'bloat', 'degenerative myelopathy'],
            'labrador retriever': ['obesity', 'hip dysplasia', 'eye problems'],
            'bulldog': ['breathing problems', 'skin issues', 'joint problems'],
            'poodle': ['hip dysplasia', 'epilepsy', 'eye problems'],
            'beagle': ['obesity', 'epilepsy', 'hypothyroidism'],
            'rottweiler': ['bloat', 'cancer', 'joint problems'],
            # Add more breeds as needed
        }
    
    def _load_vaccination_schedules(self) -> Dict[str, Dict]:
        """Load vaccination schedules"""
        return {
            'DHPP': {'puppy': [6, 9, 12, 16], 'adult_annual': True, 'core': True},
            'Rabies': {'puppy': [16], 'adult_annual': True, 'core': True},
            'Bordetella': {'puppy': [8], 'adult_annual': True, 'core': False},
            'Lyme': {'puppy': [12, 16], 'adult_annual': True, 'core': False},
        }
    
    def _load_medication_interactions(self) -> Dict[str, List[str]]:
        """Load known medication interactions"""
        return {
            'prednisone': ['nsaids', 'insulin'],
            'aspirin': ['warfarin', 'prednisone'],
            'furosemide': ['digoxin', 'aminoglycosides'],
            # Add more interactions as needed
        }
    
    def _extract_chronic_conditions(self, description: str) -> List[str]:
        """Extract chronic conditions from text description"""
        chronic_conditions = []
        condition_keywords = {
            'diabetes': ['diabetes', 'diabetic'],
            'arthritis': ['arthritis', 'joint pain', 'stiff joints'],
            'heart disease': ['heart murmur', 'heart disease', 'cardiac'],
            'kidney disease': ['kidney', 'renal', 'urinary'],
            'allergies': ['allergic', 'allergy', 'itching', 'skin reaction']
        }
        
        description_lower = description.lower()
        for condition, keywords in condition_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                chronic_conditions.append(condition)
        
        return chronic_conditions
    
    def _identify_risk_factors(self, profile: PetHealthProfile, symptoms_history: List) -> List[str]:
        """Identify risk factors from profile and symptoms"""
        risk_factors = []
        
        # Age-based risks
        if profile.age_months and profile.age_months > 84:
            risk_factors.append('senior age')
        
        # Weight-based risks
        if profile.weight_kg and profile.breed:
            # This would need breed-specific weight ranges
            # Simplified check for now
            if profile.weight_kg > 40:  # Large dog
                risk_factors.append('large breed size')
        
        # Symptom-based risks
        symptom_risk_map = {
            'vomiting': 'gastrointestinal issues',
            'diarrhea': 'gastrointestinal issues',
            'lethargy': 'systemic illness',
            'limping': 'orthopedic issues',
            'difficulty breathing': 'respiratory issues'
        }
        
        for symptom in symptoms_history:
            if isinstance(symptom, str):
                for risk_symptom, risk_factor in symptom_risk_map.items():
                    if risk_symptom in symptom.lower():
                        risk_factors.append(risk_factor)
        
        return list(set(risk_factors))
    
    def _analyze_vaccination_status(self, vaccination_records: List[CareRecord]) -> Dict[str, Any]:
        """Analyze vaccination status"""
        vaccination_status = {}
        
        for record in vaccination_records:
            vaccine_name = record.title
            vaccination_status[vaccine_name] = {
                'last_date': record.date_occurred.isoformat(),
                'due_date': self._calculate_next_vaccination_date(vaccine_name, record.date_occurred)
            }
        
        return vaccination_status
    
    def _check_overdue_vaccinations(self, profile: PetHealthProfile) -> List[str]:
        """Check for overdue vaccinations"""
        overdue = []
        current_date = datetime.now()
        
        for vaccine, status in profile.vaccination_status.items():
            if 'due_date' in status and status['due_date']:
                due_date = datetime.fromisoformat(status['due_date'].replace('Z', '+00:00'))
                if due_date < current_date:
                    overdue.append(vaccine)
        
        return overdue
    
    def _check_medication_interactions(self, medications: List[str]) -> List[str]:
        """Check for medication interactions"""
        interactions = []
        
        for i, med1 in enumerate(medications):
            med1_lower = med1.lower()
            for med2 in medications[i+1:]:
                med2_lower = med2.lower()
                
                if med1_lower in self.medication_interactions:
                    if any(interaction in med2_lower for interaction in self.medication_interactions[med1_lower]):
                        interactions.append(f"{med1} with {med2}")
        
        return interactions
    
    def _calculate_next_checkup(self, profile: PetHealthProfile) -> Optional[str]:
        """Calculate recommended next checkup date"""
        if not profile.last_checkup:
            return datetime.now().isoformat()
        
        last_checkup = datetime.fromisoformat(profile.last_checkup.replace('Z', '+00:00'))
        
        # Senior pets need checkups every 6 months
        if profile.age_months and profile.age_months > 84:
            next_checkup = last_checkup + timedelta(days=180)
        else:
            next_checkup = last_checkup + timedelta(days=365)
        
        return next_checkup.isoformat()
    
    def _check_preventive_care_due(self, profile: PetHealthProfile) -> List[str]:
        """Check what preventive care is due"""
        due_care = []
        
        # Check vaccinations
        overdue_vaccines = self._check_overdue_vaccinations(profile)
        due_care.extend([f"{vaccine} vaccination" for vaccine in overdue_vaccines])
        
        # Check routine care based on age
        if profile.age_months:
            if profile.age_months >= 6 and profile.age_months <= 12:
                due_care.append("Spay/neuter consultation")
            if profile.age_months >= 12:
                due_care.append("Annual dental checkup")
        
        return due_care
    
    def _calculate_next_vaccination_date(self, vaccine_name: str, last_date: datetime) -> str:
        """Calculate next vaccination due date"""
        # Simplified - most vaccines are annual
        next_date = last_date + timedelta(days=365)
        return next_date.isoformat()
    
    def _get_breed_specific_recommendations(self, breed: str) -> List[str]:
        """Get breed-specific health recommendations"""
        breed_lower = breed.lower()
        
        breed_recommendations = {
            'golden retriever': [
                'Regular hip and elbow screening',
                'Heart health monitoring',
                'Cancer awareness and early detection'
            ],
            'german shepherd': [
                'Hip dysplasia screening',
                'Bloat prevention measures',
                'Neurological health monitoring'
            ],
            'bulldog': [
                'Respiratory health monitoring',
                'Weight management crucial',
                'Skin fold care and cleaning'
            ]
        }
        
        return breed_recommendations.get(breed_lower, ['Breed-specific care consultation with vet'])
    
    def _get_weight_recommendations(self, profile: PetHealthProfile) -> List[str]:
        """Get weight-specific recommendations"""
        recommendations = []
        
        # This would need breed-specific weight ranges
        # Simplified logic for demonstration
        if profile.weight_kg:
            if profile.weight_kg > 30:  # Large dog
                recommendations.extend([
                    'Joint health support supplements',
                    'Controlled exercise routine',
                    'Regular weight monitoring'
                ])
            elif profile.weight_kg < 5:  # Small dog
                recommendations.extend([
                    'Frequent small meals',
                    'Temperature regulation care',
                    'Gentle exercise appropriate for size'
                ])
        
        return recommendations
    
    def _is_checkup_overdue(self, profile: PetHealthProfile) -> bool:
        """Check if routine checkup is overdue"""
        if not profile.last_checkup:
            return True
        
        last_checkup = datetime.fromisoformat(profile.last_checkup.replace('Z', '+00:00'))
        current_date = datetime.now()
        
        # Senior pets need checkups every 6 months
        if profile.age_months and profile.age_months > 84:
            return (current_date - last_checkup).days > 180
        else:
            return (current_date - last_checkup).days > 365

    async def emergency_health_triage(self, user_id: int, query: str, pet_name: str = None) -> Dict[str, Any]:
        """Perform emergency health triage with context"""
        try:
            # Get pet profile for context
            profile = await self._build_pet_health_profile(user_id, pet_name)
            
            # Analyze query urgency with pet context
            urgency_analysis = await self._analyze_emergency_with_context(query, profile)
            
            # Generate contextual emergency response
            response = await self._generate_emergency_response(query, profile, urgency_analysis)
            
            return {
                'urgency_level': urgency_analysis['urgency_level'],
                'response': response,
                'immediate_actions': urgency_analysis['immediate_actions'],
                'vet_required': urgency_analysis['vet_required'],
                'timeframe': urgency_analysis['timeframe']
            }
            
        except Exception as e:
            logger.error(f"Error in emergency triage: {str(e)}")
            return {
                'urgency_level': 4,
                'response': "I'm unable to assess this situation properly. Please contact your veterinarian immediately if you're concerned about your pet's health.",
                'immediate_actions': ["Contact veterinarian", "Monitor pet closely"],
                'vet_required': True,
                'timeframe': "Immediately"
            }
    
    async def _analyze_emergency_with_context(self, query: str, profile: PetHealthProfile) -> Dict[str, Any]:
        """Analyze emergency situation with pet-specific context"""
        try:
            # Enhanced emergency keywords with severity
            emergency_indicators = {
                'seizure': 5, 'unconscious': 5, 'not breathing': 5, 'bleeding heavily': 5,
                'bloat': 4, 'difficulty breathing': 4, 'severe vomiting': 4, 'collapse': 4,
                'limping': 2, 'vomiting': 3, 'diarrhea': 2, 'not eating': 2
            }
            
            base_urgency = 1
            immediate_actions = []
            
            query_lower = query.lower()
            
            # Check for emergency indicators
            for indicator, urgency in emergency_indicators.items():
                if indicator in query_lower:
                    base_urgency = max(base_urgency, urgency)
            
            # Adjust urgency based on pet profile
            if profile.age_months:
                if profile.age_months < 6 or profile.age_months > 84:
                    base_urgency = min(base_urgency + 1, 5)  # Young or senior pets are higher risk
            
            # Check for breed-specific risks
            if profile.breed and 'bloat' in query_lower:
                high_risk_breeds = ['german shepherd', 'great dane', 'standard poodle']
                if profile.breed.lower() in high_risk_breeds:
                    base_urgency = 5
                    immediate_actions.append("Go to emergency vet immediately - high risk breed for bloat")
            
            # Determine immediate actions and timeframe
            if base_urgency >= 5:
                immediate_actions.extend([
                    "Go to emergency veterinary hospital immediately",
                    "Call ahead to alert them of your arrival",
                    "Keep pet calm and comfortable during transport"
                ])
                timeframe = "Immediately"
                vet_required = True
            elif base_urgency >= 4:
                immediate_actions.extend([
                    "Contact your veterinarian immediately",
                    "Monitor symptoms closely",
                    "Prepare for possible emergency visit"
                ])
                timeframe = "Within 1 hour"
                vet_required = True
            elif base_urgency >= 3:
                immediate_actions.extend([
                    "Call your veterinarian for guidance",
                    "Monitor pet closely",
                    "Note any changes in symptoms"
                ])
                timeframe = "Within 2-4 hours"
                vet_required = True
            else:
                immediate_actions.extend([
                    "Monitor pet for any worsening symptoms",
                    "Consider scheduling a routine vet visit"
                ])
                timeframe = "Monitor for 24 hours"
                vet_required = False
            
            return {
                'urgency_level': base_urgency,
                'immediate_actions': immediate_actions,
                'vet_required': vet_required,
                'timeframe': timeframe
            }
            
        except Exception as e:
            logger.error(f"Error analyzing emergency: {str(e)}")
            return {
                'urgency_level': 4,
                'immediate_actions': ["Contact veterinarian"],
                'vet_required': True,
                'timeframe': "Immediately"
            }
    
    async def _generate_emergency_response(self, query: str, profile: PetHealthProfile, urgency: Dict) -> str:
        """Generate contextual emergency response"""
        try:
            context_info = []
            
            if profile.pet_name:
                context_info.append(f"Pet: {profile.pet_name}")
            if profile.breed:
                context_info.append(f"Breed: {profile.breed}")
            if profile.age_months:
                age_years = profile.age_months // 12
                context_info.append(f"Age: {age_years} years")
            if profile.chronic_conditions:
                context_info.append(f"Known conditions: {', '.join(profile.chronic_conditions)}")
            
            context_text = " | ".join(context_info) if context_info else ""
            
            prompt = f"""
            You are an emergency veterinary triage AI. Provide immediate guidance for this situation.
            
            Emergency Query: {query}
            Pet Context: {context_text}
            Assessed Urgency Level: {urgency['urgency_level']}/5
            
            Provide a clear, actionable response that:
            1. Addresses the immediate concern
            2. Takes into account the pet's specific context
            3. Provides clear next steps
            4. Emphasizes safety and urgency appropriately
            
            Be direct and helpful while emphasizing professional veterinary care when needed.
            """
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            # Add urgency indicators
            if urgency['urgency_level'] >= 4:
                response_text = f"🚨 HIGH PRIORITY HEALTH CONCERN 🚨\n\n{response.content}"
            elif urgency['urgency_level'] >= 3:
                response_text = f"⚠️ URGENT ATTENTION NEEDED ⚠️\n\n{response.content}"
            else:
                response_text = response.content
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating emergency response: {str(e)}")
            return "I'm unable to provide specific guidance right now. Please contact your veterinarian immediately if you're concerned about your pet's health." 