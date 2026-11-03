from django.urls import path
from . import views

urlpatterns=[
    path('<int:group_id>/invite-helper/<int:helper_id>/',views.invite_group_helper,name='invite_group_helper'),
    path('invitations/<int:invitation_id>/<str:answer>/',views.answer_group_invitation,name='answer_group_invitation'),
    path('<int:group_id>/withdraw-helper/',views.withdraw_group_invitation,name='withdraw_group_invitation'),
    path('',views.my_groups,name='my_groups'),
    path('start/<int:topic_id>/',views.start_group,name='start_group'),
    path('<int:group_id>/',views.group_detail,name='group_detail'),
    path('<int:group_id>/edit/',views.edit_group,name='edit_group'),
    path('<int:group_id>/join/',views.join_group,name='join_group'),
    path('<int:group_id>/leave/',views.leave_group,name='leave_group'),
    path('<int:group_id>/close/',views.close_group,name='close_group'),
    path('messages/<int:message_id>/delete/',views.delete_group_message,name='delete_group_message'),
]
