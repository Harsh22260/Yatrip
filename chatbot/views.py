from rest_framework.views import APIView
from rest_framework.response import Response
from sentence_transformers import SentenceTransformer
from chatbot.models import KnowledgeDocument
from django.db import connection
from django.conf import settings
from groq import Groq
import json

class ChatbotQueryView(APIView):
    def post(self, request):
        try:
            query = request.data.get("query")
            if not query:
                return Response({"error": "query required"}, status=400)

            # 1️⃣ Encode query to embedding
            model = SentenceTransformer('all-MiniLM-L6-v2')
            q_emb = model.encode(query).tolist()  # list of floats

            # 2️⃣ Convert embedding to JSON string for Postgres vector comparison
            q_emb_str = json.dumps(q_emb)

            # 3️⃣ Retrieve top 5 similar docs using pgvector operator
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT title, content, metadata
                    FROM chatbot_knowledgedocument
                    ORDER BY embedding <-> %s::vector
                    LIMIT 5;
                """, [q_emb_str])
                docs = cur.fetchall()

            if not docs:
                return Response({"message": "No matching results found."}, status=200)

            # 4️⃣ Combine retrieved docs into context
            context_text = "\n\n".join([f"{d[0]}: {d[1]}" for d in docs])
            prompt = f"""
            You are Yatrip AI Assistant.
            Use the info below to help travelers with practical, short, clear answers.
            Context:\n{context_text}\n
            Question: {query}
            """

            # 5️⃣ Call Groq LLaMA3 API
            client = Groq(api_key=settings.GROQ_API_KEY)
            chat_completion = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": "You are Yatrip AI Assistant."},
                    {"role": "user", "content": prompt}
                ],
            )
            answer = chat_completion.choices[0].message["content"]

            return Response({
                "question": query,
                "answer": answer,
                "sources": [d[0] for d in docs]
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)