#!/usr/bin/env python
"""
Test for the create_or_find_episode function
"""

import unittest
from unittest.mock import patch, MagicMock
import logging

from agir_db.models.episode import Episode, EpisodeStatus
from src.evolution.a_create_or_find_episode import create_or_find_episode


class TestCreateOrFindEpisode(unittest.TestCase):
    """Test cases for create_or_find_episode function"""
    
    @patch('src.evolution.a_create_or_find_episode.get_db')
    @patch('src.evolution.a_create_or_find_episode.get_learner')
    def test_find_existing_episode(self, mock_get_learner, mock_get_db):
        """Test finding an existing running episode"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_session
        
        # Create mock existing episode
        mock_existing_episode = MagicMock(spec=Episode)
        mock_existing_episode.id = 123
        mock_existing_episode.scenario_id = 456
        mock_existing_episode.status = EpisodeStatus.RUNNING
        
        # Setup query mock to return the existing episode
        mock_session.query.return_value.filter.return_value.first.return_value = mock_existing_episode
        
        # Call the function
        result = create_or_find_episode(456)
        
        # Assertions
        self.assertEqual(result, mock_existing_episode)
        mock_session.add.assert_not_called()  # Should not add a new episode
        mock_session.commit.assert_not_called()  # Should not commit transaction
    
    @patch('src.evolution.a_create_or_find_episode.get_db')
    @patch('src.evolution.a_create_or_find_episode.get_learner')
    def test_create_new_episode(self, mock_get_learner, mock_get_db):
        """Test creating a new episode when none exists"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_session
        
        # Setup query mock to return no existing episodes
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            None,  # First call returns None for existing episode
            MagicMock()  # Second call returns a scenario
        ]
        
        # Setup mock learner
        mock_learner = MagicMock()
        mock_learner.id = 789
        mock_get_learner.return_value = mock_learner
        
        # Call the function
        result = create_or_find_episode(456)
        
        # Assertions
        self.assertIsNotNone(result)
        mock_session.add.assert_called_once()  # Should add a new episode
        mock_session.commit.assert_called_once()  # Should commit transaction
        
        # Verify episode was created with correct attributes
        created_episode = mock_session.add.call_args[0][0]
        self.assertEqual(created_episode.scenario_id, 456)
        self.assertEqual(created_episode.status, EpisodeStatus.RUNNING)
        self.assertEqual(created_episode.initiator_id, 789)
    
    @patch('src.evolution.a_create_or_find_episode.get_db')
    def test_scenario_not_found(self, mock_get_db):
        """Test handling scenario not found case"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_session
        
        # Setup query mock to return no existing episodes and no scenario
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            None,  # First call returns None for existing episode
            None   # Second call returns None for scenario
        ]
        
        # Call the function
        result = create_or_find_episode(456)
        
        # Assertions
        self.assertIsNone(result)
        mock_session.add.assert_not_called()  # Should not add a new episode
        mock_session.commit.assert_not_called()  # Should not commit transaction
    
    @patch('src.evolution.a_create_or_find_episode.get_db')
    def test_database_exception(self, mock_get_db):
        """Test handling database exceptions"""
        # Setup mocks
        mock_session = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_session
        
        # Setup query mock to raise an exception
        mock_session.query.side_effect = Exception("Database error")
        
        # Call the function
        result = create_or_find_episode(456)
        
        # Assertions
        self.assertIsNone(result)
        mock_session.rollback.assert_called_once()  # Should rollback transaction
        

if __name__ == '__main__':
    unittest.main() 