from rest_framework import status, permissions, generics, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from datetime import timedelta

from .models import User, Voter, Admin, InecOfficial
from .serializers import (
    UserSerializer, VoterSerializer, AdminSerializer, InecOfficialSerializer,
    LoginSerializer, RegistrationSerializer, PasswordChangeSerializer,
)
from .serializers import AdminCreateSerializer, InecOfficialCreateSerializer


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        print(f"🔍 Registration request received: {request.data}")
        
        serializer = RegistrationSerializer(data=request.data)
        print(f"🔍 Serializer created: {serializer}")
        
        if serializer.is_valid():
            print("✅ Serializer is valid, creating user...")
            try:
                user = serializer.save()
                print(f"✅ User created: {user}")
                
                token, created = Token.objects.get_or_create(user=user)
                print(f"✅ Token created: {token.key[:10]}...")
                
                # Get voter profile for response
                voter_profile = None
                if hasattr(user, 'voter'):
                    voter_attr = getattr(user, 'voter', None)
                    if voter_attr is not None:
                        voter_profile = VoterSerializer(voter_attr).data
                    print(f"✅ Voter profile: {voter_profile}")
                
                response_data = {
                    'user': UserSerializer(user).data,
                    'profile': voter_profile,
                    'token': token.key,
                    'message': 'Registration successful! Your account is pending INEC verification.',
                    'status': 'pending_verification'
                }
                print(f"✅ Sending response: {response_data}")
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                print(f"❌ Error during user creation: {e}")
                print(f"❌ Error type: {type(e)}")
                import traceback
                print(f"❌ Traceback: {traceback.format_exc()}")
                
                return Response({
                    'error': 'Registration failed during user creation',
                    'details': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            print(f"❌ Serializer validation failed: {serializer.errors}")
            return Response({
                'error': 'Registration failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            # Safely access validated_data
            validated_data = getattr(serializer, 'validated_data', {})
            user = validated_data.get('user') if isinstance(validated_data, dict) else None
            if user:
                token, created = Token.objects.get_or_create(user=user)
                
                # Get user profile based on role
                profile_data = None
                verification_status = None
                
                if hasattr(user, 'voter'):
                    voter_attr = getattr(user, 'voter', None)
                    if voter_attr is not None:
                        profile_data = VoterSerializer(voter_attr).data
                        verification_status = {
                            'verified': getattr(voter_attr, 'registration_verified', False),
                            'can_vote': getattr(voter_attr, 'can_vote', False)
                        }
                elif hasattr(user, 'admin'):
                    admin_attr = getattr(user, 'admin', None)
                    if admin_attr is not None:
                        profile_data = AdminSerializer(admin_attr).data
                elif hasattr(user, 'inecofficial'):
                    inec_attr = getattr(user, 'inecofficial', None)
                    if inec_attr is not None:
                        profile_data = InecOfficialSerializer(inec_attr).data
                
                return Response({
                    'user': UserSerializer(user).data,
                    'profile': profile_data,
                    'verification_status': verification_status,
                    'token': token.key,
                    'message': 'Login successful'
                }, status=status.HTTP_200_OK)
        
        return Response({
            'error': 'Login failed',
            'message': 'Invalid phone number or password. Please check your credentials and try again.',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Delete the token
            request.user.auth_token.delete()
            logout(request)
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
        except:
            return Response({
                'error': 'Logout failed'
            }, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        user_data = UserSerializer(user).data
        
        # Get role-specific profile
        profile_data = None
        if hasattr(user, 'voter'):
            voter_attr = getattr(user, 'voter', None)
            if voter_attr is not None:
                profile_data = VoterSerializer(voter_attr).data
        elif hasattr(user, 'admin'):
            admin_attr = getattr(user, 'admin', None)
            if admin_attr is not None:
                profile_data = AdminSerializer(admin_attr).data
        elif hasattr(user, 'inecofficial'):
            inec_attr = getattr(user, 'inecofficial', None)
            if inec_attr is not None:
                profile_data = InecOfficialSerializer(inec_attr).data
        
        return Response({
            'user': user_data,
            'profile': profile_data
        }, status=status.HTTP_200_OK)


class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            try:
                user = serializer.save()
                return Response({
                    'message': 'Password changed successfully'
                }, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({
                    'error': 'Failed to change password',
                    'details': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'error': 'Password change failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
"""
class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            # In a real implementation, you would send an SMS or email with a reset token
            # For now, we'll just return a success message
            return Response({
                'message': 'Password reset instructions have been sent to your phone number.'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Failed to process password reset request',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                return Response({
                    'message': 'Password has been reset successfully. You can now login with your new password.'
                }, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({
                    'error': 'Failed to reset password',
                    'details': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'error': 'Password reset failed',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
"""


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_list(request):
    """List all users (Admin only)"""
    if not hasattr(request.user, 'admin'):
        return Response({
            'error': 'Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    users = User._default_manager.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def voter_list(request):
    """Deprecated: use VoterListView for paginated/filterable list."""
    user = request.user
    if not (user.is_superuser or hasattr(user, 'admin') or hasattr(user, 'inecofficial')):
        return Response({
            'error': 'Admin or INEC Official access required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    voters = Voter._default_manager.all()
    serializer = VoterSerializer(voters, many=True)
    return Response(serializer.data)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 200


class VoterListView(generics.ListAPIView):
    """Paginated, searchable list of voters for Admin/INEC officials."""
    serializer_class = VoterSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__name', 'voter_id', 'voters_card_id', 'user__phone_number']
    ordering_fields = ['user__name', 'voter_id']

    def get_queryset(self):
        user = self.request.user
        if not (user.is_superuser or hasattr(user, 'admin') or hasattr(user, 'inecofficial')):
            return Voter._default_manager.none()

        qs = Voter._default_manager.select_related('user').all()

        # registration_verified filter (expects true/false)
        rv = self.request.query_params.get('registration_verified')
        if rv is not None:
            if rv.lower() in ['true', '1', 'yes']:
                qs = qs.filter(registration_verified=True)
            elif rv.lower() in ['false', '0', 'no']:
                qs = qs.filter(registration_verified=False)

        return qs


class VoterDetailView(generics.RetrieveAPIView):
    """Retrieve a single voter by voter_id (Admin/INEC only)."""
    serializer_class = VoterSerializer
    lookup_field = 'voter_id'
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not (user.is_superuser or hasattr(user, 'admin') or hasattr(user, 'inecofficial')):
            return Voter._default_manager.none()
        return Voter._default_manager.select_related('user').all()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def voter_history(request, voter_id):
    """Return voting history for a given voter (Admin/INEC only)."""
    user = request.user
    if not (user.is_superuser or hasattr(user, 'admin') or hasattr(user, 'inecofficial')):
        return Response({'error': 'Admin or INEC Official access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        voter = Voter._default_manager.get(voter_id=voter_id)
    except Voter._default_manager.model.DoesNotExist:
        return Response({'error': 'Voter not found'}, status=status.HTTP_404_NOT_FOUND)

    from voting.serializers import VoteSerializer
    votes = voter.votes.all().order_by('-timestamp')
    serializer = VoteSerializer(votes, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_voter_registration(request, voter_id):
    """Verify voter registration against INEC database"""
    user = request.user
    # Allow INEC officials, admin users, or superusers to verify voters
    if not (user.is_superuser or hasattr(user, 'admin') or hasattr(user, 'inecofficial')):
        return Response({
            'error': 'INEC Official or Admin access required'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        voter = Voter._default_manager.get(voter_id=voter_id)
        
        # Simulate verification without external database
        voter.registration_verified = True
        voter.can_vote = True
        voter.save()
        
        return Response({
            'message': f'Voter {voter.voter_id} verification successful',
            'voter': VoterSerializer(voter).data
        }, status=status.HTTP_200_OK)
    
    except Exception:
        return Response({
            'error': 'Voter not found'
        }, status=status.HTTP_404_NOT_FOUND)



@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cancel_voter_registration(request, voter_id):
    """Cancel/Reject a voter registration - only Admins/INEC Officials/Superusers"""
    user = request.user
    if not (user.is_superuser or hasattr(user, 'admin') or hasattr(user, 'inecofficial')):
        return Response({'error': 'INEC Official or Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        voter = Voter._default_manager.get(voter_id=voter_id)
        voter.registration_verified = False
        voter.can_vote = False
        voter.save()

        return Response({'message': f'Voter {voter.voter_id} registration cancelled', 'voter': VoterSerializer(voter).data}, status=status.HTTP_200_OK)
    except Voter._default_manager.model.DoesNotExist:
        return Response({'error': 'Voter not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': 'Failed to cancel registration', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_admin(request):
    """Only superusers can create admin users"""
    user = request.user
    if not user.is_superuser:
        return Response({'error': 'Superuser access required'}, status=status.HTTP_403_FORBIDDEN)

    serializer = AdminCreateSerializer(data=request.data)
    if serializer.is_valid():
        try:
            new_user = serializer.save()
            return Response({'user': UserSerializer(new_user).data, 'message': 'Admin created successfully'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': 'Failed to create admin', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({'error': 'Invalid data', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_inec_official(request):
    """Superusers and Admins can create INEC Officials. Admins cannot create Admins."""
    user = request.user
    if not (user.is_superuser or hasattr(user, 'admin')):
        return Response({'error': 'Superuser or Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    serializer = InecOfficialCreateSerializer(data=request.data)
    if serializer.is_valid():
        try:
            new_user = serializer.save()
            return Response({'user': UserSerializer(new_user).data, 'message': 'INEC Official created successfully'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': 'Failed to create INEC Official', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({'error': 'Invalid data', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)