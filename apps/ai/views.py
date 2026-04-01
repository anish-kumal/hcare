from django.db.models import Q
from apps.doctors.models import Doctor
from .schemas import DoctorSchema
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from django.views.generic import ListView
from django.contrib import messages

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # other params...
)


def ai_specialty_search(query: str) -> str | None:

    # Use stored doctor specializations as the only allowed output values.
    available_specialties = list(
        Doctor.objects.filter(
            specialization__isnull=False
        ).exclude(
            specialization=''
        ).values_list('specialization', flat=True).distinct()
    )
    if not available_specialties:
        return None


    prompt = f"""
            You are an AI assistant that helps users find the most relevant doctor based on their symptoms or concerns.

            The user said: "{query}"

            Instructions:
            - The text may be in English, or contain spelling mistakes.
            - If the input seems random, meaningless, or unrelated to health, respond with: "No valid medical concern detected."
            - If the input describes a medical symptom, return only **one** specialty from this list: "{available_specialties}"
        

            Guidelines:
            - Use your understanding of common health terms in  English.
            - Choose the specialty that best fits the described symptom (e.g., heart → Cardiologist, mental health → Psychiatrist, ear/nose/throat → ENT, etc.).
            - Do not explain or add extra text. Return only the specialty name or "No valid medical concern detected."
        """

    try:
        structured_llm = llm.with_structured_output(DoctorSchema)
        response = structured_llm.invoke(prompt)
    except Exception:
        return None

    detected_specialty = (getattr(response, 'name', '') or '').strip()
    if not detected_specialty or detected_specialty.lower().startswith('no valid medical concern detected'):
        return None

    return detected_specialty




class DoctorListView( ListView):
    """List all available doctors for booking"""
    template_name = 'appointments/doctor_list.html'
    context_object_name = 'doctors'
    paginate_by = 12
    
    def get_queryset(self):
        self.ai_detected_specialization = None

        queryset = Doctor.objects.filter(
            is_available=True,
            is_active=True
        ).select_related('user', 'hospital').prefetch_related('schedules')
        
        # Filter by specialization if provided
        selected_specialization = self.request.GET.get('specialization', '').strip()
        if selected_specialization:
            queryset = queryset.filter(specialization=selected_specialization)
        
        ai_query = self.request.GET.get('ai_query', '').strip()
        search_query = self.request.GET.get('q', '').strip()

        # Smart search mode: map symptom text to a specialization first.
        if ai_query:
            detected_specialization = ai_specialty_search(ai_query)
            self.ai_detected_specialization = detected_specialization

            if detected_specialization and detected_specialization != "Only use English language":
                queryset = queryset.filter(
                    Q(specialization__iexact=detected_specialization)
                    | Q(specialization__icontains=detected_specialization)
                )
            elif detected_specialization == "Only use English language":
                # Send warning message and return empty queryset
                messages.warning(self.request, "Only use English language")
                self.ai_detected_specialization = "Only use English language"
                queryset = queryset.none()
            else:
                queryset = queryset.filter(
                    Q(user__first_name__icontains=ai_query)
                    | Q(user__last_name__icontains=ai_query)
                    | Q(specialization__icontains=ai_query)
                )

        # Normal search mode.
        elif search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query)
                | Q(user__last_name__icontains=search_query)
                | Q(user__username__icontains=search_query)
                | Q(specialization__icontains=search_query)
                | Q(hospital__name__icontains=search_query)
            )
        
        return queryset.order_by('user__first_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get unique specialization values (CharField), filter out empty ones
        specs = Doctor.objects.filter(
            specialization__isnull=False
        ).exclude(
            specialization=''
        ).values_list('specialization', flat=True).distinct().order_by('specialization')
        context['specializations'] = specs
        context['selected_specialization'] = self.request.GET.get('specialization', '').strip()
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['ai_query'] = self.request.GET.get('ai_query', '').strip()
        context['ai_detected_specialization'] = self.ai_detected_specialization
        return context
