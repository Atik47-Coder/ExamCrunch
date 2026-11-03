from django.shortcuts import render,redirect

FEATURES=[
    ('bi-bar-chart-line','','Difficulty dashboard',
     'See which topics the whole class finds hardest, so revision time goes where it matters.'),
    ('bi-diagram-3','green','Explainable matching',
     'Every suggested helper comes with a reason: who can explain, and how busy they are.'),
    ('bi-incognito','pink','Anonymous questions',
     'Ask without anyone knowing it was you. Only you and the moderators can see your name.'),
    ('bi-people','amber','Study groups',
     'When 3 or more classmates are stuck on a topic, you can start a group and meet together.'),
    ('bi-collection','red','Resource library',
     'Share notes, PDFs and links by topic. Files are private to your course.'),
    ('bi-calendar-event','','Exam countdown',
     'Moderators set the exam date, and everyone sees how many days are left.'),
]

def home(request):
    if request.user.is_authenticated:
        return redirect('my_courses')
    return render(request,'home.html',{'features':FEATURES})
